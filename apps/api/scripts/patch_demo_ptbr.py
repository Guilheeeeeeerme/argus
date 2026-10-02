#!/usr/bin/env python3
"""One-off idempotent patch: make the demo tenancy read as Brazilian (pt-BR).

Anchors on the stable demo UUIDs (seed_demo), never on company data, so it is
safe to re-run and never touches customer rows. Translates only known legacy
English LLM outputs (detections.summary, prompt_hits[].rationale, feedback
reasoning); anything unmapped is listed for review and left untouched.

Usage:
  patch_demo_ptbr.py [--apply]   # default is dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from demo_catalog import CAMERAS  # noqa: E402
from seed_demo import (  # noqa: E402
    CAMERA_DEMO_ID,
    COMPANY_DEMO_ID,
    ESTABLISHMENT_DEMO_ID,
    PROMPT_SET_ID,
    SANDBOX_COMPANY_ID,
    WEBHOOK_ID,
)

from argus.config import settings  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

COMPANY_NAME = "Argus Demo Brasil"
SANDBOX_NAME = "Sandbox de Demonstração"
WEBHOOK_NAME = "Contexto externo de demonstração"
ADDRESS = "São Paulo, SP, Brasil"
TIMEZONE = "America/Sao_Paulo"
LEGACY_SITE_NAMES = {"Demo Establishment"}
LEGACY_ADDRESSES = {"US-101, San Luis Obispo, California", "New Address 42"}
LEGACY_TIMEZONES = {"America/Los_Angeles", "UTC"}
# Old English catalog names per catalog index, plus the pre-catalog camera.
LEGACY_CAMERA_NAMES = {
    0: {"US-101 — Broad Street", "Cam 01 — Lobby"},
    1: {"US-101 — Monterey Street"},
    2: {"US-101 — Madonna Road"},
}
LEGACY_PROMPT_SET_NAMES = {
    "Default watchlist",
    "Traffic density and queues",
    "Roadway activity and obstructions",
    "Vehicle mix and traffic conditions",
}
LEGACY_PROMPT_PREFIXES = (
    "Are one or more cars",
    "Is there a clearly visible",
    "Are vehicles clearly",
    "Is a person or substantial",
    "Are cars, trucks",
    "Is an unusually dense",
    "Is there an unauthorized person",
)

# Known legacy English LLM outputs -> pt-BR. Never guess beyond this map.
# The free-form VLM summaries below were transcribed verbatim from the demo
# database (2026-10-02) and hand-translated; keep keys byte-exact.
SUMMARY_TRANSLATIONS = {
    "Person in restricted area": "Pessoa em área restrita",
    "Person visible": "Pessoa visível",
    "No match (mock).": "Nenhum acerto (mock).",
    "Suspicious loitering detected near restricted shelf area.": "Comportamento suspeito perto da área restrita da loja.",
    "Deterministic mock VLM hit.": "Acerto determinístico do VLM (mock).",
    "The image shows a nighttime traffic scene on a multi-lane highway (101 at Madonna Rd). Several cars are clearly visible with their headlights on, travelling along the road under low-visibility, dark conditions. There are no unusually dense queues or visible obstructions present in the travel lanes.":
        "A imagem mostra uma cena de tráfego noturna em uma rodovia com várias faixas (101 na Madonna Rd). Vários carros estão claramente visíveis com os faróis acesos, circulando na via em condições de baixa visibilidade e escuridão. Não há filas incomumente densas nem obstruções visíveis nas faixas de rolamento.",
    "Cars are visible in the travel lanes, but there is no dense queue or obstruction.":
        "Carros visíveis nas faixas de rolamento, sem fila densa ou obstrução.",
    "Vehicles are visible traveling on the highway under nighttime conditions, with headlights and taillights creating light streaks.":
        "Veículos circulam pela rodovia à noite, com faróis e lanternas formando rastros de luz.",
    "The frame shows a nighttime view of a roadway (101 at Broad St) with minimal visible traffic. A distant car is faintly visible on the roadway.":
        "O frame mostra uma via à noite (101 na Broad St) com pouco tráfego visível. Um carro ao longe aparece discretamente na pista.",
    "The image shows a nighttime highway scene with faint vehicle lights visible in the distance, but no dense queue or traffic obstruction.":
        "A imagem mostra uma rodovia à noite com luzes fracas de veículos ao longe, sem fila densa ou obstrução no tráfego.",
    "Vehicles are visible in the travel lanes, but there is no dense queue or obstruction.":
        "Veículos visíveis nas faixas de rolamento, sem fila densa ou obstrução.",
    "One car is visible in the travel lanes, but no dense queue or obstruction is present.":
        "Um carro visível nas faixas de rolamento, sem fila densa ou obstrução.",
    "The image shows a nighttime traffic scene on a highway with visible vehicle lights and some traffic present in the travel lanes.":
        "A imagem mostra uma cena de tráfego noturna em rodovia, com luzes de veículos e algum tráfego nas faixas de rolamento.",
    "One car is visible on the road, with no unusual traffic density or obstruction.":
        "Um carro visível na pista, sem densidade de tráfego incomum ou obstrução.",
    "A distant car is visible on the road in normal traffic conditions.":
        "Um carro ao longe na pista, em condições normais de tráfego.",
    "The image shows a nighttime view of a highway (101 at Broad St). Traffic is visible with headlights and taillights indicating movement, but no dense queue or obstruction is present.":
        "A imagem mostra uma rodovia à noite (101 na Broad St). Há tráfego visível, com faróis e lanternas indicando movimento, mas sem fila densa ou obstrução.",
    "The frame shows a highway view at night with vehicle headlights and taillights visible traveling on the road.":
        "O frame mostra uma rodovia à noite, com faróis e lanternas de veículos circulando na pista.",
    "The image shows a nighttime traffic view on a highway (101 at Broad St). Headlight streaks and vehicle lights are visible traveling along the roadway, but individual vehicles cannot be distinctly counted due to motion blur and lighting. There is no dense queue or obstruction occupying a travel lane.":
        "A imagem mostra uma rodovia à noite (101 na Broad St). Há rastros de faróis e luzes de veículos circulando na pista, mas os veículos individuais não podem ser contados com precisão devido ao desfoque de movimento e à iluminação. Não há fila densa ou obstrução ocupando uma faixa de rolamento.",
    "A distant car is clearly visible on the road under normal visibility conditions.":
        "Um carro ao longe está claramente visível na pista, em condições normais de visibilidade.",
    "At least one car is clearly visible in the travel lanes.":
        "Ao menos um carro está claramente visível nas faixas de rolamento.",
    "At least one vehicle (car) is visible in the travel lanes in the distance.":
        "Ao menos um veículo (carro) é visível ao longe nas faixas de rolamento.",
    "Cars are clearly visible on the road, with approximately one vehicle distinguishable in the frame.":
        "Carros claramente visíveis na pista, com aproximadamente um veículo distinguível no frame.",
    "Distant vehicle lights are visible on the roadway.":
        "Luzes de veículos ao longe são visíveis na pista.",
    "One or more cars are clearly visible in the travel lanes.":
        "Um ou mais carros estão claramente visíveis nas faixas de rolamento.",
    "Vehicle headlights and taillights are visible along the highway lanes, indicating normal traffic presence.":
        "Faróis e lanternas são visíveis ao longo das faixas da rodovia, indicando tráfego normal.",
    "Vehicle light streaks are clearly visible on the roadway indicating traffic movement, though individual vehicle counts cannot be reliably determined.":
        "Rastros de luz de veículos são claramente visíveis na pista, indicando movimento do tráfego, mas a contagem individual de veículos não pode ser determinada com confiabilidade.",
    "Vehicles are visible on the roadway, indicated by their bright headlights and taillight streaks.":
        "Veículos são visíveis na pista, indicados por faróis brilhantes e rastros de lanternas.",
    "Vehicles with visible headlights and taillights are present in the travel lanes.":
        "Veículos com faróis e lanternas visíveis estão presentes nas faixas de rolamento.",
    "Vehicles with visible headlights and taillights are present on the roadway.":
        "Veículos com faróis e lanternas visíveis estão presentes na pista.",
}

APPLY = False


def _site_id(index: int) -> str:
    return str(ESTABLISHMENT_DEMO_ID if index == 0 else uuid.uuid5(COMPANY_DEMO_ID, CAMERAS[index]["key"] + ":site"))


def _camera_id(index: int) -> str:
    return str(CAMERA_DEMO_ID if index == 0 else uuid.uuid5(COMPANY_DEMO_ID, CAMERAS[index]["key"] + ":camera"))


def _set_id(index: int) -> str:
    return str(PROMPT_SET_ID if index == 0 else uuid.uuid5(COMPANY_DEMO_ID, CAMERAS[index]["key"] + ":prompts"))


async def patch(session_factory) -> list[str]:
    report: list[str] = []

    def note(msg: str) -> None:
        report.append(msg if APPLY else f"(dry) {msg}")

    async with session_factory() as session:
        # RLS is enforced (FORCE) even for the table owner: policies key off the
        # app.current_role GUC. Act as platform root so legacy rows are visible
        # and writable; without this the patch silently sees nothing.
        await session.execute(
            text("SELECT set_config('app.current_role', 'root', true)")
        )
        # Companies (demo + sandbox) by fixed IDs.
        rows = (await session.execute(
            text("SELECT id, name FROM companies WHERE id IN (:a, :b)"),
            {"a": str(COMPANY_DEMO_ID), "b": str(SANDBOX_COMPANY_ID)},
        )).all()
        for rid, name in rows:
            rid = str(rid)
            target = COMPANY_NAME if rid == str(COMPANY_DEMO_ID) else SANDBOX_NAME
            if name != target:
                if APPLY:
                    await session.execute(
                        text("UPDATE companies SET name = :n WHERE id = :id"),
                        {"n": target, "id": rid},
                    )
                note(f"company {rid[:8]}: {name!r} -> {target!r}")

        # Establishments and cameras of the demo company (fixed + uuid5 anchors).
        for index, item in enumerate(CAMERAS):
            est = (await session.execute(
                text("SELECT name, address, timezone FROM establishments WHERE id = :id"),
                {"id": _site_id(index)},
            )).first()
            if est is not None:
                name, address, timezone = est
                needs = (
                    name in LEGACY_SITE_NAMES
                    or "San Luis Obispo" in (name or "")
                    or (address or "") in LEGACY_ADDRESSES
                    or (timezone or "") in LEGACY_TIMEZONES
                )
                if needs:
                    if APPLY:
                        await session.execute(
                            text(
                                "UPDATE establishments SET name = :n, address = :a, "
                                "timezone = :tz WHERE id = :id"
                            ),
                            {"n": item["site"], "a": ADDRESS, "tz": TIMEZONE, "id": _site_id(index)},
                        )
                    note(f"establishment {_site_id(index)[:8]}: {name!r} -> {item['site']!r}")

            cam = (await session.execute(
                text("SELECT name FROM cameras WHERE id = :id"),
                {"id": _camera_id(index)},
            )).first()
            if cam is not None and cam[0] in LEGACY_CAMERA_NAMES.get(index, set()):
                if APPLY:
                    await session.execute(
                        text("UPDATE cameras SET name = :n WHERE id = :id"),
                        {"n": item["name"], "id": _camera_id(index)},
                    )
                note(f"camera {_camera_id(index)[:8]}: {cam[0]!r} -> {item['name']!r}")

            ps = (await session.execute(
                text("SELECT name FROM prompt_sets WHERE id = :id"),
                {"id": _set_id(index)},
            )).first()
            if ps is not None and ps[0] in LEGACY_PROMPT_SET_NAMES:
                if APPLY:
                    await session.execute(
                        text("UPDATE prompt_sets SET name = :n WHERE id = :id"),
                        {"n": item["watchlist"], "id": _set_id(index)},
                    )
                note(f"prompt_set {_set_id(index)[:8]}: {ps[0]!r} -> {item['watchlist']!r}")

            prompts = (await session.execute(
                text(
                    "SELECT id, text FROM prompts WHERE prompt_set_id = :sid "
                    "ORDER BY sort_order ASC"
                ),
                {"sid": _set_id(index)},
            )).all()
            for order, (pid, ptext) in enumerate(prompts):
                is_legacy = ptext in {"Is there an unauthorized person in a restricted area?"} or str(ptext).startswith(LEGACY_PROMPT_PREFIXES)
                if is_legacy and order < len(item["prompts"]):
                    if APPLY:
                        await session.execute(
                            text("UPDATE prompts SET text = :t WHERE id = :id"),
                            {"t": item["prompts"][order], "id": str(pid)},
                        )
                    note(f"prompt {str(pid)[:8]}: translated")

        # Webhook endpoint (fixed ID).
        wh = (await session.execute(
            text("SELECT name FROM webhook_endpoints WHERE id = :id"),
            {"id": str(WEBHOOK_ID)},
        )).first()
        if wh is not None and wh[0] in {"Demo inbound context"}:
            if APPLY:
                await session.execute(
                    text("UPDATE webhook_endpoints SET name = :n WHERE id = :id"),
                    {"n": WEBHOOK_NAME, "id": str(WEBHOOK_ID)},
                )
            note(f"webhook {str(WEBHOOK_ID)[:8]}: {wh[0]!r} -> {WEBHOOK_NAME!r}")

        # Legacy English LLM outputs — known strings only.
        detections = (await session.execute(
            text("SELECT id, summary, prompt_hits FROM detections")
        )).all()
        for did, summary, hits in detections:
            changed = False
            new_summary = SUMMARY_TRANSLATIONS.get(summary or "", summary)
            if new_summary != summary:
                changed = True
            new_hits = hits
            if hits:
                new_hits = json.loads(hits) if isinstance(hits, str) else json.loads(json.dumps(hits))
                for hit in new_hits:
                    if not isinstance(hit, dict):
                        continue
                    if hit.get("rationale") in SUMMARY_TRANSLATIONS:
                        hit["rationale"] = SUMMARY_TRANSLATIONS[hit["rationale"]]
                        changed = True
                    for field in ("name", "text"):
                        if hit.get(field) in SUMMARY_TRANSLATIONS:
                            hit[field] = SUMMARY_TRANSLATIONS[hit[field]]
                            changed = True
            if changed:
                if APPLY:
                    await session.execute(
                        text("UPDATE detections SET summary = :s, prompt_hits = :h WHERE id = :id"),
                        {"s": new_summary, "h": json.dumps(new_hits, ensure_ascii=False) if hits else hits, "id": str(did)},
                    )
                note(f"detection {str(did)[:8]}: {summary!r} -> {new_summary!r}")

        feedbacks = (await session.execute(
            text("SELECT id, reasoning FROM feedback")
        )).all()
        for fid, reasoning in feedbacks:
            if (reasoning or "") in SUMMARY_TRANSLATIONS:
                if APPLY:
                    await session.execute(
                        text("UPDATE feedback SET reasoning = :r WHERE id = :id"),
                        {"r": SUMMARY_TRANSLATIONS[reasoning], "id": str(fid)},
                    )
                note(f"feedback {str(fid)[:8]}: {reasoning!r} -> {SUMMARY_TRANSLATIONS[reasoning]!r}")

        if APPLY:
            await session.commit()

    # Anything left untranslated for human review (never auto-guessed).
    async with session_factory() as session:
        await session.execute(
            text("SELECT set_config('app.current_role', 'root', true)")
        )
        leftovers = (await session.execute(
            text(
                "SELECT id, summary FROM detections "
                "WHERE summary IS NOT NULL AND summary !~ '[À-ü]'"
            )
        )).all()
        for did, summary in leftovers:
            if summary not in SUMMARY_TRANSLATIONS.values():
                report.append(f"REVIEW detection {str(did)[:8]}: {summary!r}")
        fb_left = (await session.execute(
            text("SELECT id, reasoning FROM feedback WHERE reasoning IS NOT NULL AND reasoning !~ '[À-ü]'")
        )).all()
        for fid, reasoning in fb_left:
            if reasoning not in SUMMARY_TRANSLATIONS.values():
                report.append(f"REVIEW feedback {str(fid)[:8]}: {reasoning!r}")

    return report


async def main() -> int:
    global APPLY
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    args = parser.parse_args()
    APPLY = args.apply

    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
    )
    try:
        report = await patch(async_sessionmaker(engine, expire_on_commit=False))
    finally:
        await engine.dispose()

    if not report:
        print("Nothing to change — demo tenancy is already pt-BR.")
    for line in report:
        print(line)
    print(f"{'APPLIED' if APPLY else 'DRY-RUN'}: {len(report)} change(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

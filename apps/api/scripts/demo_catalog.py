"""Official public demo feeds: stable HLS master playlists (not temporary segments).

Narrative (Option A — monitoramento municipal):
  One Brazilian operator account watches two related districts of the same
  demonstration operation — vias (tráfego) and orla (costa) — with Portuguese
  PromptSets that match each camera's real scene.

Sources (subject to provider terms; feeds may go offline):
- Caltrans District 5 CCTV — highway traffic (named honestly, not as Brazilian streets)
- Beach TV / TripSmarter — coastal tourism live channels
- CoastalCOMs (AU) — coastal promenade / harbour webcams
"""

SOURCE_PAGE = "https://cwwp2.dot.ca.gov/data/d5/cctv/cctvStatusD05.json"
SOURCE_TERMS = "https://dot.ca.gov/conditions-of-use"

SOURCES = (
    {
        "name": "Caltrans District 5 CCTV",
        "page": SOURCE_PAGE,
        "terms": SOURCE_TERMS,
    },
    {
        "name": "Beach TV (TripSmarter)",
        "page": "https://www.beachtv.net/",
        "terms": "https://www.beachtv.net/",
    },
    {
        "name": "CoastalCOMs webcams",
        "page": "https://www.coastalcoms.com/",
        "terms": "https://www.coastalcoms.com/",
    },
)

# Prior catalog watchlist names — re-seed renames these; operator renames are kept.
LEGACY_WATCHLIST_NAMES = frozenset(
    {
        "Default watchlist",
        "Densidade de tráfego e filas",
        "Atividade na via e obstruções",
        "Tipos de veículos e condições do tráfego",
        "Veículos e filas na US-101",
        "Composição do tráfego na US-101",
        "Tráfego e obstáculos na via",
        "Veículos e filas na via",
        "Composição do tráfego",
        "Praia, orla e pessoas",
        "Orla, ondas e pedestres",
        "Ornitorrinco e atividade no recinto",
        "Coala e presença humana no habitat",
        "Veículos na via expressa",
        "Filas e bloqueios na via",
        "Mistura de veículos",
        "Pessoas na orla",
        "Costa e embarcações",
        "Banhistas e pedestres",
        "Promenade e acesso à orla",
    }
)

# Prior catalog prompt texts — re-seed upgrades these, but never operator-custom text.
LEGACY_PROMPT_TEXTS = frozenset(
    {
        "Is there an unauthorized person in a restricted area?",
        "Há um ou mais carros, caminhões, ônibus ou motos claramente visíveis nas faixas de rolamento? Descreva o tráfego visível e dê contagens aproximadas apenas quando for possível distinguir. Esta é uma observação rotineira de tráfego, não um alarme de incidente.",
        "Há uma fila densa ou uma obstrução claramente visível ocupando uma faixa de rolamento? Descreva a posição em relação à imagem e a incerteza. Não deduza velocidade, tempo parado, colisão, identidade ou intenção a partir de um único frame. Reflexo e escuridão não são evidência de incidente.",
        "Há veículos claramente visíveis nesta via ou área de incorporação? Descreva a distribuição deles pela imagem e os tipos de veículo quando for possível distinguir. Relate apenas a evidência visível; não estime velocidade nem leia placas.",
        "Há uma pessoa ou objeto de grande porte claramente visível dentro de uma faixa de rolamento, formando possível obstrução? Diferencie um veículo que apenas aparece em um frame de um veículo confirmadamente parado. Não deduza intenção, identidade, acidente ou direção do movimento. Indique a incerteza quando houver oclusão.",
        "Há carros, caminhões ou ônibus claramente visíveis na pista? Resuma a mistura e a distribuição dos veículos visíveis, com contagens aproximadas apenas quando for possível distinguir. Mencione reflexo, escuridão ou baixa visibilidade. Esta é uma observação rotineira de tráfego.",
        "Há uma fila muito densa ou uma obstrução claramente visível em uma faixa de rolamento? Descreva a localização usando termos relativos à imagem. Não afirme movimento na contramão, tempo parado, colisão, identidades ou velocidade a partir deste único snapshot. Retorne nenhum acerto quando a evidência for insuficiente.",
        "Há veículos claramente distinguíveis (carro, caminhão, ônibus ou moto) nas faixas ou acostamento? Descreva tipos e contagem aproximada só quando for possível separar uns dos outros. Não leia placas, não estime velocidade e não infira identidade. Escuridão, reflexo ou blur sem veículo claro = sem acerto.",
        "Há fila densa ou objeto/veículo claramente ocupando uma faixa de rolamento de forma a sugerir bloqueio? Descreva a posição relativa na imagem e a incerteza. Não afirme colisão, tempo parado, intenção ou direção do movimento a partir de um único frame. Evidência fraca = sem acerto.",
        "Há veículos claramente visíveis na pista ou na área de incorporação? Relate distribuição e tipos só com evidência visual. Não estime velocidade, não leia placas e não invente veículos parcialmente oclusos. Sem veículo distinguível = sem acerto.",
        "Há pessoa a pé ou objeto de grande porte claramente dentro de uma faixa de rolamento (possível obstrução)? Diferencie veículo em trânsito de pessoa/objeto na faixa. Não deduza acidente, intenção ou identidade. Oclusão ou dúvida = sem acerto.",
        "Há carros, caminhões ou ônibus claramente visíveis na pista? Resuma a mistura visível e conte só quando for possível distinguir. Mencione baixa visibilidade se ela impedir a leitura. Sem veículos claros = sem acerto.",
        "Há congestionamento denso ou bloqueio claramente visível em pelo menos uma faixa? Localize em termos relativos à imagem. Não afirme contramão, colisão, identidades ou velocidade a partir deste snapshot. Evidência insuficiente = sem acerto.",
        "Há pessoas claramente visíveis na praia, no píer, na orla ou em um deck costeiro? Descreva posição relativa e se estão sozinhas ou em grupo só quando for óbvio. Não infira identidade, idade, intenção ou atividade além do visível. Sem pessoa distinguível (ex.: só vinheta/TV) = sem acerto.",
        "Há água costeira, ondas, faixa de areia/rocha ou embarcação claramente visíveis? Descreva apenas o que aparece no quadro. Não invente condição de surf, maré, perigo ou clima. Cena indoor/estúdio sem orla = sem acerto.",
        "Há pedestres ou banhistas claramente visíveis na areia, no calçadão ou junto à água? Descreva posição relativa na imagem. Não leia rostos, não estime idade e não invente incidentes. Sem pessoa clara = sem acerto.",
        "Há ondas quebrando, linha de costa, píer ou embarcação claramente visíveis? Relate só evidência no frame. Não deduza direção do vento, altura de onda numérica ou risco. Sem cena costeira distinguível = sem acerto.",
        "Há um ou mais ornitorrincos (platypus) claramente visíveis na água ou na margem do recinto? Descreva posição e oclusão. Não invente outros animais nem conte silhuetas ambíguas. Sem animal distinguível = sem acerto.",
        "Há uma pessoa (tratador/visitante) claramente visível junto ao habitat? Descreva só o que é óbvio no frame. Não infira identidade, função exata ou interação além do visível. Sem pessoa clara = sem acerto.",
        "Há um ou mais coalas claramente visíveis em árvore, galho ou chão do recinto? Descreva posição relativa e se estão parados ou se movendo só quando for evidente. Não invente filhotes oclusos. Sem coala distinguível = sem acerto.",
        "Há uma pessoa claramente visível no habitat ou na área imediatamente adjacente à câmera? Não infira identidade nem intenção. Sem pessoa clara = sem acerto.",
    }
)

# Prior playlists — re-seed refreshes these URLs to the current catalog.
LEGACY_PLAYLISTS = frozenset(
    {
        "https://wzmedia.dot.ca.gov/D5/101atBroadSt.stream/playlist.m3u8",
        "https://wzmedia.dot.ca.gov/D5/101atMontereySt.stream/playlist.m3u8",
        "https://wzmedia.dot.ca.gov/D5/101atMadonnaRd.stream/playlist.m3u8",
        "https://5ed325193d4e1.streamlock.net:444/LiveTV/KTVHD/playlist.m3u8",
        "https://5ed325193d4e1.streamlock.net:444/LiveTV/MTVHD/playlist.m3u8",
        "https://zssd-platypus.hls.camzonecdn.com/CamzoneStreams/zssd-platypus/Playlist.m3u8",
        "https://zssd-koala.hls.camzonecdn.com/CamzoneStreams/zssd-koala/Playlist.m3u8",
        "https://streaming-au.coastalcoms.com/cw/ballinarmscamera.stream/playlist.m3u8",
        "https://streaming-au.coastalcoms.com/cw/forstercamera.stream/playlist.m3u8",
        "https://streaming-au.coastalcoms.com/cw/brunswickheadscamera.stream/playlist.m3u8",
    }
)

LEGACY_CAMERA_NAMES = frozenset(
    {
        "US-101 — Broad Street",
        "US-101 — Monterey Street",
        "US-101 — Madonna Road",
        "Beach TV — Key West & Florida Keys",
        "Beach TV — Myrtle Beach",
        "San Diego Zoo — Platypus Cam",
        "San Diego Zoo — Koala Cam",
        "Marginal Pinheiros — Cidade Jardim",
        "Av. 23 de Maio — Bela Vista",
        "Marginal Tietê — Santana",
        "Praia — Key West e Florida Keys",
        "Praia — Myrtle Beach",
        "Zoológico — Ornitorrinco",
    }
)

# Two estabelecimentos × three cameras. Verified reachable HLS masters (HTTP 200).
UNITS = (
    {
        "key": "distrito-vias",
        "name": "Distrito Vias — Trânsito",
        "address": "Operação municipal · vias (feeds públicos Caltrans D5)",
        "timezone": "America/Sao_Paulo",
        "cameras": (
            {
                # Stable fixture key → CAMERA_DEMO_ID / PROMPT_SET_ID
                "key": "broad-street",
                "name": "Câmera Via 101 — Broad Street",
                "playlist": "https://wzmedia.dot.ca.gov/D5/101atBroadSt.stream/playlist.m3u8",
                "watchlist": "Veículos na via expressa",
                "prompts": (
                    "Há veículos claramente distinguíveis (carro, caminhão, ônibus ou moto) nas faixas ou acostamento? Descreva tipos e contagem aproximada só quando for possível separar uns dos outros. Não leia placas, não estime velocidade e não infira identidade. Escuridão, reflexo ou blur sem veículo claro = sem acerto.",
                    "Há fila densa ou objeto/veículo claramente ocupando uma faixa de rolamento de forma a sugerir bloqueio? Descreva a posição relativa na imagem e a incerteza. Não afirme colisão, tempo parado, intenção ou direção do movimento a partir de um único frame. Evidência fraca = sem acerto.",
                ),
            },
            {
                "key": "monterey-street",
                "name": "Câmera Via 101 — Monterey Street",
                "playlist": "https://wzmedia.dot.ca.gov/D5/101atMontereySt.stream/playlist.m3u8",
                "watchlist": "Filas e bloqueios na via",
                "prompts": (
                    "Há veículos claramente visíveis na pista ou na área de incorporação? Relate distribuição e tipos só com evidência visual. Não estime velocidade, não leia placas e não invente veículos parcialmente oclusos. Sem veículo distinguível = sem acerto.",
                    "Há pessoa a pé ou objeto de grande porte claramente dentro de uma faixa de rolamento (possível obstrução)? Diferencie veículo em trânsito de pessoa/objeto na faixa. Não deduza acidente, intenção ou identidade. Oclusão ou dúvida = sem acerto.",
                ),
            },
            {
                "key": "madonna-road",
                "name": "Câmera Via 101 — Madonna Road",
                "playlist": "https://wzmedia.dot.ca.gov/D5/101atMadonnaRd.stream/playlist.m3u8",
                "watchlist": "Mistura de veículos",
                "prompts": (
                    "Há carros, caminhões ou ônibus claramente visíveis na pista? Resuma a mistura visível e conte só quando for possível distinguir. Mencione baixa visibilidade se ela impedir a leitura. Sem veículos claros = sem acerto.",
                    "Há congestionamento denso ou bloqueio claramente visível em pelo menos uma faixa? Localize em termos relativos à imagem. Não afirme contramão, colisão, identidades ou velocidade a partir deste snapshot. Evidência insuficiente = sem acerto.",
                ),
            },
        ),
    },
    {
        "key": "distrito-orla",
        "name": "Distrito Orla — Costa",
        "address": "Operação municipal · orla e turismo (feeds públicos Beach TV / CoastalCOMs)",
        "timezone": "America/Sao_Paulo",
        "cameras": (
            {
                # Unit UUID preserved via legacy key-west-beach:site in seed_demo.
                "key": "key-west-beach",
                "name": "Câmera Praia Key West",
                "playlist": "https://5ed325193d4e1.streamlock.net:444/LiveTV/KTVHD/playlist.m3u8",
                "watchlist": "Pessoas na orla",
                "prompts": (
                    "Há pessoas claramente visíveis na praia, no píer, na orla ou em um deck costeiro? Descreva posição relativa e se estão sozinhas ou em grupo só quando for óbvio. Não infira identidade, idade, intenção ou atividade além do visível. Sem pessoa distinguível (ex.: só vinheta/TV) = sem acerto.",
                    "Há água costeira, ondas, faixa de areia/rocha ou embarcação claramente visíveis? Descreva apenas o que aparece no quadro. Não invente condição de surf, maré, perigo ou clima. Cena indoor/estúdio sem orla = sem acerto.",
                ),
            },
            {
                "key": "myrtle-beach",
                "name": "Câmera Praia Myrtle Beach",
                "playlist": "https://5ed325193d4e1.streamlock.net:444/LiveTV/MTVHD/playlist.m3u8",
                "watchlist": "Banhistas e pedestres",
                "prompts": (
                    "Há pedestres ou banhistas claramente visíveis na areia, no calçadão ou junto à água? Descreva posição relativa na imagem. Não leia rostos, não estime idade e não invente incidentes. Sem pessoa clara = sem acerto.",
                    "Há ondas quebrando, linha de costa, píer ou embarcação claramente visíveis? Relate só evidência no frame. Não deduza direção do vento, altura de onda numérica ou risco. Sem cena costeira distinguível = sem acerto.",
                ),
            },
            {
                "key": "ballina-orla",
                "name": "Câmera Orla Ballina",
                "playlist": "https://streaming-au.coastalcoms.com/cw/ballinarmscamera.stream/playlist.m3u8",
                "watchlist": "Promenade e acesso à orla",
                "prompts": (
                    "Há pedestres, ciclistas ou veículos claramente visíveis no calçadão, na promenade ou no acesso à orla? Descreva posição relativa e densidade só quando for óbvio. Não infira identidade nem intenção. Sem pessoa/veículo distinguível = sem acerto.",
                    "Há linha de costa, água, píer, porto ou estrutura de orla claramente visíveis? Relate só o que aparece no quadro. Não invente maré, perigo ou clima. Sem cena costeira = sem acerto.",
                ),
            },
        ),
    },
)

# Flat camera list for callers that only need playlists / prompts.
CAMERAS = tuple(
    {
        "key": camera["key"],
        "unit_key": unit["key"],
        "name": camera["name"],
        "site": unit["name"],
        "address": unit["address"],
        "timezone": unit["timezone"],
        "playlist": camera["playlist"],
        "watchlist": camera["watchlist"],
        "prompts": camera["prompts"],
    }
    for unit in UNITS
    for camera in unit["cameras"]
)

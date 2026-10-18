"""Official public demo feeds: stable HLS master playlists (not temporary segments).

Shape: one account, two estabelecimentos, three cameras each.

Sources (subject to provider terms; feeds may go offline):
- Caltrans District 5 CCTV — traffic (stand-in for São Paulo vias)
- Beach TV / TripSmarter — coastal tourism live channels
- San Diego Zoo Camzone CDN — habitat live cam
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
        "name": "San Diego Zoo Live Cams",
        "page": "https://zoo.sandiegozoo.org/live-cameras",
        "terms": "https://zoo.sandiegozoo.org/terms-of-use",
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
        "Praia, orla e pessoas",
        "Orla, ondas e pedestres",
        "Ornitorrinco e atividade no recinto",
        "Coala e presença humana no habitat",
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

# Two estabelecimentos × three cameras. Verified reachable HLS masters (HTTP 200).
UNITS = (
    {
        "key": "sp-trafego",
        "name": "São Paulo — Trânsito",
        "address": "São Paulo, SP, Brasil",
        "timezone": "America/Sao_Paulo",
        "cameras": (
            {
                # Stable fixture key → CAMERA_DEMO_ID / PROMPT_SET_ID
                "key": "broad-street",
                "name": "Marginal Pinheiros — Cidade Jardim",
                "playlist": "https://wzmedia.dot.ca.gov/D5/101atBroadSt.stream/playlist.m3u8",
                "watchlist": "Veículos e filas na via",
                "prompts": (
                    "Há veículos claramente distinguíveis (carro, caminhão, ônibus ou moto) nas faixas ou acostamento? Descreva tipos e contagem aproximada só quando for possível separar uns dos outros. Não leia placas, não estime velocidade e não infira identidade. Escuridão, reflexo ou blur sem veículo claro = sem acerto.",
                    "Há fila densa ou objeto/veículo claramente ocupando uma faixa de rolamento de forma a sugerir bloqueio? Descreva a posição relativa na imagem e a incerteza. Não afirme colisão, tempo parado, intenção ou direção do movimento a partir de um único frame. Evidência fraca = sem acerto.",
                ),
            },
            {
                "key": "monterey-street",
                "name": "Av. 23 de Maio — Bela Vista",
                "playlist": "https://wzmedia.dot.ca.gov/D5/101atMontereySt.stream/playlist.m3u8",
                "watchlist": "Tráfego e obstáculos na via",
                "prompts": (
                    "Há veículos claramente visíveis na pista ou na área de incorporação? Relate distribuição e tipos só com evidência visual. Não estime velocidade, não leia placas e não invente veículos parcialmente oclusos. Sem veículo distinguível = sem acerto.",
                    "Há pessoa a pé ou objeto de grande porte claramente dentro de uma faixa de rolamento (possível obstrução)? Diferencie veículo em trânsito de pessoa/objeto na faixa. Não deduza acidente, intenção ou identidade. Oclusão ou dúvida = sem acerto.",
                ),
            },
            {
                "key": "madonna-road",
                "name": "Marginal Tietê — Santana",
                "playlist": "https://wzmedia.dot.ca.gov/D5/101atMadonnaRd.stream/playlist.m3u8",
                "watchlist": "Composição do tráfego",
                "prompts": (
                    "Há carros, caminhões ou ônibus claramente visíveis na pista? Resuma a mistura visível e conte só quando for possível distinguir. Mencione baixa visibilidade se ela impedir a leitura. Sem veículos claros = sem acerto.",
                    "Há congestionamento denso ou bloqueio claramente visível em pelo menos uma faixa? Localize em termos relativos à imagem. Não afirme contramão, colisão, identidades ou velocidade a partir deste snapshot. Evidência insuficiente = sem acerto.",
                ),
            },
        ),
    },
    {
        "key": "costa-habitat",
        "name": "Costa e Habitat",
        "address": "Orla costeira e habitat de observação (feeds públicos)",
        "timezone": "America/Sao_Paulo",
        "cameras": (
            {
                # Unit UUID preserved via legacy key-west-beach:site in seed_demo.
                "key": "key-west-beach",
                "name": "Praia — Key West e Florida Keys",
                "playlist": "https://5ed325193d4e1.streamlock.net:444/LiveTV/KTVHD/playlist.m3u8",
                "watchlist": "Praia, orla e pessoas",
                "prompts": (
                    "Há pessoas claramente visíveis na praia, no píer, na orla ou em um deck costeiro? Descreva posição relativa e se estão sozinhas ou em grupo só quando for óbvio. Não infira identidade, idade, intenção ou atividade além do visível. Sem pessoa distinguível (ex.: só vinheta/TV) = sem acerto.",
                    "Há água costeira, ondas, faixa de areia/rocha ou embarcação claramente visíveis? Descreva apenas o que aparece no quadro. Não invente condição de surf, maré, perigo ou clima. Cena indoor/estúdio sem orla = sem acerto.",
                ),
            },
            {
                "key": "myrtle-beach",
                "name": "Praia — Myrtle Beach",
                "playlist": "https://5ed325193d4e1.streamlock.net:444/LiveTV/MTVHD/playlist.m3u8",
                "watchlist": "Orla, ondas e pedestres",
                "prompts": (
                    "Há pedestres ou banhistas claramente visíveis na areia, no calçadão ou junto à água? Descreva posição relativa na imagem. Não leia rostos, não estime idade e não invente incidentes. Sem pessoa clara = sem acerto.",
                    "Há ondas quebrando, linha de costa, píer ou embarcação claramente visíveis? Relate só evidência no frame. Não deduza direção do vento, altura de onda numérica ou risco. Sem cena costeira distinguível = sem acerto.",
                ),
            },
            {
                "key": "sdz-platypus",
                "name": "Zoológico — Ornitorrinco",
                "playlist": "https://zssd-platypus.hls.camzonecdn.com/CamzoneStreams/zssd-platypus/Playlist.m3u8",
                "watchlist": "Ornitorrinco e atividade no recinto",
                "prompts": (
                    "Há um ou mais ornitorrincos (platypus) claramente visíveis na água ou na margem do recinto? Descreva posição e oclusão. Não invente outros animais nem conte silhuetas ambíguas. Sem animal distinguível = sem acerto.",
                    "Há uma pessoa (tratador/visitante) claramente visível junto ao habitat? Descreva só o que é óbvio no frame. Não infira identidade, função exata ou interação além do visível. Sem pessoa clara = sem acerto.",
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

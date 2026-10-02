"""Official public Caltrans feeds; stable master playlists, not temporary segments."""

SOURCE_PAGE = "https://cwwp2.dot.ca.gov/data/d5/cctv/cctvStatusD05.json"
SOURCE_TERMS = "https://dot.ca.gov/conditions-of-use"

CAMERAS = (
    {
        "key": "broad-street",
        "name": "Marginal Pinheiros — Cidade Jardim",
        "site": "São Paulo — Cidade Jardim",
        "playlist": "https://wzmedia.dot.ca.gov/D5/101atBroadSt.stream/playlist.m3u8",
        "watchlist": "Densidade de tráfego e filas",
        "prompts": (
            "Há um ou mais carros, caminhões, ônibus ou motos claramente visíveis nas faixas de rolamento? Descreva o tráfego visível e dê contagens aproximadas apenas quando for possível distinguir. Esta é uma observação rotineira de tráfego, não um alarme de incidente.",
            "Há uma fila densa ou uma obstrução claramente visível ocupando uma faixa de rolamento? Descreva a posição em relação à imagem e a incerteza. Não deduza velocidade, tempo parado, colisão, identidade ou intenção a partir de um único frame. Reflexo e escuridão não são evidência de incidente.",
        ),
    },
    {
        "key": "monterey-street",
        "name": "Av. 23 de Maio — Bela Vista",
        "site": "São Paulo — Bela Vista",
        "playlist": "https://wzmedia.dot.ca.gov/D5/101atMontereySt.stream/playlist.m3u8",
        "watchlist": "Atividade na via e obstruções",
        "prompts": (
            "Há veículos claramente visíveis nesta via ou área de incorporação? Descreva a distribuição deles pela imagem e os tipos de veículo quando for possível distinguir. Relate apenas a evidência visível; não estime velocidade nem leia placas.",
            "Há uma pessoa ou objeto de grande porte claramente visível dentro de uma faixa de rolamento, formando possível obstrução? Diferencie um veículo que apenas aparece em um frame de um veículo confirmadamente parado. Não deduza intenção, identidade, acidente ou direção do movimento. Indique a incerteza quando houver oclusão.",
        ),
    },
    {
        "key": "madonna-road",
        "name": "Marginal Tietê — Santana",
        "site": "São Paulo — Santana",
        "playlist": "https://wzmedia.dot.ca.gov/D5/101atMadonnaRd.stream/playlist.m3u8",
        "watchlist": "Tipos de veículos e condições do tráfego",
        "prompts": (
            "Há carros, caminhões ou ônibus claramente visíveis na pista? Resuma a mistura e a distribuição dos veículos visíveis, com contagens aproximadas apenas quando for possível distinguir. Mencione reflexo, escuridão ou baixa visibilidade. Esta é uma observação rotineira de tráfego.",
            "Há uma fila muito densa ou uma obstrução claramente visível em uma faixa de rolamento? Descreva a localização usando termos relativos à imagem. Não afirme movimento na contramão, tempo parado, colisão, identidades ou velocidade a partir deste único snapshot. Retorne nenhum acerto quando a evidência for insuficiente.",
        ),
    },
)

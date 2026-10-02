"""Official public Caltrans feeds; stable master playlists, not temporary segments."""

SOURCE_PAGE = "https://cwwp2.dot.ca.gov/data/d5/cctv/cctvStatusD05.json"
SOURCE_TERMS = "https://dot.ca.gov/conditions-of-use"

CAMERAS = (
    {
        "key": "broad-street",
        "name": "US-101 — Broad Street",
        "site": "San Luis Obispo — Broad Street",
        "playlist": "https://wzmedia.dot.ca.gov/D5/101atBroadSt.stream/playlist.m3u8",
        "watchlist": "Traffic density and queues",
        "prompts": (
            "Are one or more cars, trucks, buses or motorcycles clearly visible in the travel lanes? Describe the visible traffic and approximate counts only when distinguishable. This is a normal traffic observation, not an incident alarm.",
            "Is there a clearly visible dense queue or obstruction occupying a travel lane? Describe image-relative position and uncertainty. Do not infer speed, stopped duration, a collision, identity, or intent from one frame. Glare and darkness are not evidence of an incident.",
        ),
    },
    {
        "key": "monterey-street",
        "name": "US-101 — Monterey Street",
        "site": "San Luis Obispo — Monterey Street",
        "playlist": "https://wzmedia.dot.ca.gov/D5/101atMontereySt.stream/playlist.m3u8",
        "watchlist": "Roadway activity and obstructions",
        "prompts": (
            "Are vehicles clearly visible on this roadway or merge area? Describe their distribution across the image and vehicle types when distinguishable. Report visible evidence only; do not estimate speed or read license plates.",
            "Is a person or substantial object clearly visible within a travel lane, creating a possible obstruction? Distinguish a vehicle merely visible in one frame from a confirmed stopped vehicle. Do not infer intent, identity, an accident, or motion direction. State uncertainty when occluded.",
        ),
    },
    {
        "key": "madonna-road",
        "name": "US-101 — Madonna Road",
        "site": "San Luis Obispo — Madonna Road",
        "playlist": "https://wzmedia.dot.ca.gov/D5/101atMadonnaRd.stream/playlist.m3u8",
        "watchlist": "Vehicle mix and traffic conditions",
        "prompts": (
            "Are cars, trucks or buses clearly visible on the road? Summarize the visible vehicle mix and distribution, using approximate counts only when distinguishable. Mention glare, darkness or poor visibility. This is a normal traffic observation.",
            "Is an unusually dense queue or clearly visible obstruction present in a travel lane? Describe location using image-relative terms. Do not claim wrong-way movement, stopped duration, a collision, identities or speed from this single snapshot. Return no match when evidence is insufficient.",
        ),
    },
)

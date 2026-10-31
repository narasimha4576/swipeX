import re

COUNTRY_WORDS = {
    "United States": [
        "united states of america", "united states", "u.s.a.", "u.s.", "usa", "us", "new york",
        "san francisco", "seattle", "austin", "boston", "chicago", "los angeles", "palo alto",
        "mountain view", "sunnyvale", "denver", "atlanta", "miami", "dallas", "houston",
    ],
    "United Kingdom": [
        "united kingdom", "u.k.", "uk", "england", "scotland", "wales", "northern ireland",
        "great britain", "london", "manchester", "edinburgh",
    ],
    "India": [
        "india", "bengaluru", "bangalore", "hyderabad", "pune", "chennai", "mumbai", "delhi",
        "gurgaon", "gurugram", "noida", "kolkata", "ahmedabad",
    ],
    "Canada": ["canada", "toronto", "vancouver", "montreal", "ottawa", "calgary"],
    "Germany": ["germany", "deutschland", "berlin", "munich", "hamburg", "frankfurt"],
    "France": ["france", "paris", "lyon"],
    "Netherlands": ["netherlands", "amsterdam", "rotterdam", "eindhoven"],
    "Spain": ["spain", "madrid", "barcelona"],
    "Italy": ["italy", "milan", "rome"],
    "Portugal": ["portugal", "lisbon", "porto"],
    "Ireland": ["ireland", "dublin"],
    "Poland": ["poland", "warsaw", "krakow", "wroclaw"],
    "Sweden": ["sweden", "stockholm"],
    "Norway": ["norway", "oslo"],
    "Denmark": ["denmark", "copenhagen"],
    "Finland": ["finland", "helsinki"],
    "Switzerland": ["switzerland", "zurich", "geneva"],
    "Austria": ["austria", "vienna"],
    "Belgium": ["belgium", "brussels"],
    "Czech Republic": ["czech republic", "czechia", "prague"],
    "Romania": ["romania", "bucharest"],
    "Hungary": ["hungary", "budapest"],
    "Greece": ["greece", "athens"],
    "Turkey": ["turkey", "istanbul"],
    "Israel": ["israel", "tel aviv"],
    "United Arab Emirates": ["united arab emirates", "uae", "dubai", "abu dhabi"],
    "Saudi Arabia": ["saudi arabia", "riyadh"],
    "Singapore": ["singapore"],
    "Japan": ["japan", "tokyo", "osaka"],
    "South Korea": ["south korea", "korea", "seoul"],
    "China": ["china", "beijing", "shanghai", "shenzhen"],
    "Hong Kong": ["hong kong"],
    "Taiwan": ["taiwan", "taipei"],
    "Australia": ["australia", "sydney", "melbourne", "brisbane"],
    "New Zealand": ["new zealand", "auckland"],
    "Brazil": ["brazil", "brasil", "sao paulo"],
    "Mexico": ["mexico", "mexico city"],
    "Argentina": ["argentina", "buenos aires"],
    "Chile": ["chile", "santiago"],
    "Colombia": ["colombia", "bogota"],
    "South Africa": ["south africa", "cape town", "johannesburg"],
    "Nigeria": ["nigeria", "lagos"],
    "Kenya": ["kenya", "nairobi"],
    "Egypt": ["egypt", "cairo"],
    "Pakistan": ["pakistan", "karachi", "lahore"],
    "Bangladesh": ["bangladesh", "dhaka"],
    "Sri Lanka": ["sri lanka", "colombo"],
    "Philippines": ["philippines", "manila"],
    "Indonesia": ["indonesia", "jakarta"],
    "Malaysia": ["malaysia", "kuala lumpur"],
    "Thailand": ["thailand", "bangkok"],
    "Vietnam": ["vietnam", "ho chi minh", "hanoi"],
    "Ukraine": ["ukraine", "kyiv", "kiev"],
    "Estonia": ["estonia", "tallinn"],
    "Lithuania": ["lithuania", "vilnius"],
    "Latvia": ["latvia", "riga"],
    "Bulgaria": ["bulgaria", "sofia"],
    "Serbia": ["serbia", "belgrade"],
    "Croatia": ["croatia", "zagreb"],
    "Costa Rica": ["costa rica"],
}

_PATTERNS = {
    country: re.compile(
        r"(?<![a-z])(?:" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")(?![a-z])"
    )
    for country, words in COUNTRY_WORDS.items()
}

# Two-letter US state codes (the ones that cannot be confused with a country code)
_STATES = (
    "AK AZ AR CA CO CT FL GA HI IL IA KS KY LA MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR "
    "RI SC SD TN TX UT VT VA WA WV WI WY DC"
).split()
_STATE_RE = re.compile(r",\s*(?:" + "|".join(_STATES) + r")\b")


def detect_country(text: str | None) -> str | None:
    if not text:
        return None
    lowered = text.lower()
    best = None
    for country, pattern in _PATTERNS.items():
        match = pattern.search(lowered)
        if match and (best is None or match.start() < best[0]):
            best = (match.start(), country)
    if best:
        return best[1]
    if _STATE_RE.search(text):
        return "United States"
    return None
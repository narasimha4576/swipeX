from urllib.parse import quote

import httpx

API = "https://www.wikidata.org/w/api.php"
COMPANY_WORDS = (
    "company", "corporation", "software", "technology", "bank", "startup", "platform",
    "manufacturer", "business", "firm", "enterprise", "service", "multinational",
    "conglomerate", "retailer", "provider", "developer", "network", "e-commerce",
)


def find_entity(name: str, client: httpx.Client) -> dict | None:
    response = client.get(
        API,
        params={
            "action": "wbsearchentities",
            "search": name,
            "language": "en",
            "format": "json",
            "type": "item",
            "limit": 7,
        },
        timeout=10,
    )
    response.raise_for_status()
    for item in response.json().get("search", []):
        label = (item.get("label") or "").strip().lower()
        description = (item.get("description") or "").lower()
        if label == name.strip().lower() and any(w in description for w in COMPANY_WORDS):
            return item
    return None


def _claim(entity: dict, prop: str):
    best = None
    for claim in entity.get("claims", {}).get(prop, []):
        if claim.get("rank") == "deprecated":
            continue
        if claim.get("mainsnak", {}).get("snaktype") != "value":
            continue
        if best is None or claim.get("rank") == "preferred" or best.get("rank") != "preferred":
            best = claim
    return best["mainsnak"]["datavalue"]["value"] if best else None


def _label(qid: str, client: httpx.Client) -> str | None:
    response = client.get(
        API,
        params={
            "action": "wbgetentities",
            "ids": qid,
            "props": "labels",
            "languages": "en",
            "format": "json",
        },
        timeout=10,
    )
    response.raise_for_status()
    return (
        response.json().get("entities", {}).get(qid, {}).get("labels", {}).get("en", {}).get("value")
    )


def fetch_facts(qid: str, client: httpx.Client) -> dict:
    response = client.get(
        API,
        params={
            "action": "wbgetentities",
            "ids": qid,
            "props": "claims|descriptions|labels|sitelinks",
            "languages": "en",
            "sitefilter": "enwiki",
            "format": "json",
        },
        timeout=10,
    )
    response.raise_for_status()
    entity = response.json()["entities"][qid]

    founded = _claim(entity, "P571")
    employees = _claim(entity, "P1128")
    hq = _claim(entity, "P159")
    website = _claim(entity, "P856")
    logo = _claim(entity, "P154")
    image = _claim(entity, "P18")
    wiki_title = (entity.get("sitelinks", {}).get("enwiki") or {}).get("title")

    founded_year = None
    if isinstance(founded, dict) and founded.get("time"):
        try:
            founded_year = int(founded["time"][1:5])
        except ValueError:
            founded_year = None

    employee_count = None
    if isinstance(employees, dict) and employees.get("amount"):
        try:
            employee_count = int(float(employees["amount"]))
        except ValueError:
            employee_count = None

    headquarters = None
    if isinstance(hq, dict) and hq.get("id"):
        try:
            headquarters = _label(hq["id"], client)
        except Exception:
            headquarters = None

    return {
        "qid": qid,
        "label": (entity.get("labels", {}).get("en") or {}).get("value"),
        "description": (entity.get("descriptions", {}).get("en") or {}).get("value"),
        "website": website if isinstance(website, str) else None,
        "logo_url": commons_url(logo),
        "image_url": commons_url(image),
        "founded_year": founded_year,
        "employees": employee_count,
        "headquarters": headquarters,
        "wikipedia_url": (
            "https://en.wikipedia.org/wiki/" + wiki_title.replace(" ", "_") if wiki_title else None
        ),
        "wikidata_url": f"https://www.wikidata.org/wiki/{qid}",
    }


def search_companies(query: str, client: httpx.Client, limit: int = 6) -> list[dict]:
    response = client.get(
        API,
        params={
            "action": "wbsearchentities",
            "search": query,
            "language": "en",
            "format": "json",
            "type": "item",
            "limit": 10,
        },
        timeout=10,
    )
    response.raise_for_status()
    found = []
    for item in response.json().get("search", []):
        description = (item.get("description") or "").lower()
        if any(word in description for word in COMPANY_WORDS):
            found.append(
                {
                    "qid": item["id"],
                    "label": item.get("label") or item["id"],
                    "description": item.get("description") or "",
                }
            )
        if len(found) >= limit:
            break
    return found


def commons_url(filename) -> str | None:
    if not isinstance(filename, str) or not filename.strip():
        return None
    return (
        "https://commons.wikimedia.org/wiki/Special:FilePath/"
        + quote(filename.strip().replace(" ", "_"))
        + "?width=640"
    )
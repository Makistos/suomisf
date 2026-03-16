import asyncio
import aiohttp
import datetime
import re
from typing import List, Optional

from app.orm_decl import Person
from app.route_helpers import new_session
from app import app

# Cache: personid -> (timestamp, sorted list of all WikiImageInfo)
_image_cache: dict[int, tuple[datetime.datetime, list]] = {}
_CACHE_TTL = datetime.timedelta(minutes=10)

try:
    import numpy as np
    import cv2
    _face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    _profile_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_profileface.xml"
    )
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


positive_words = [
    ("portrait", 6),
    ("headshot", 6)
]

negative_words = [
    ("plaque", 10),
    ("manuscript", 10),
    ("poster", 10),
    ("logo", 10),
    ("cover", 10),
    ("signature", 6),
    ("book", 5),
    ("scan", 4),
    ("award", 2),
    ("page", 5),
    ("grave", 10),
    ("letter", 5)
]


class WikiImageInfo:
    def __init__(self, url: str, description_url: Optional[str],
                 credit: Optional[str], license: Optional[str],
                 dimensions: Optional[dict[str, int]]):
        self.url = url
        self.description_url = description_url
        self.credit = credit
        self.license = license
        self.scoring: dict[str, int] = {}
        self.score: int = 0
        self.dimensions = dimensions

    def to_dict(self):
        return {
            "url": self.url,
            "description_url": self.description_url,
            "credit": self.credit,
            "license": self.license,
            "score": self.score,
            "dimensions": self.dimensions,
            "scoring": self.scoring
        }


class PersonImageQuery:
    def __init__(self, name: str, qid: Optional[str] = None,
                 fullname: Optional[str] = None,
                 alt_name: Optional[str] = None,
                 dob: Optional[int] = None,
                 dod: Optional[int] = None):
        self.qid = qid
        self.fullname = fullname
        self.alt_name = alt_name
        self.name = name
        self.dob = dob
        self.dod = dod


# ---------- Helper functions ----------

def fix_name(name: str) -> str:
    return name.replace(" ", "_").lower()


def score_image(filename: str, person: Person,
                width: int = 0, height: int = 0) -> tuple[int, dict[str, int]]:
    """Filename heuristic scoring."""
    scoring = {}
    name = filename.lower()
    score = 0
    year_match = re.search(r"\d{4}", name)
    if year_match:
        year = int(year_match.group())
        if 1800 <= year <= datetime.date.today().year:
            scoring["year"] = 1
            score += 1
    if max(width, height) > 400:
        scoring["size"] = 2
        score += 2
    if height > width:
        scoring["orientation"] = 2
        score += 2
    names = [fix_name(n) for n in
             [person.fullname, person.alt_name, person.name] if n]
    # Collapse all non-alphanumeric sequences to "_" for separator matching
    name_normalized = re.sub(r'[^a-z0-9]+', '_', name)
    # Strip all separators for CamelCase matching ("BurroughsEdgarRice")
    name_stripped = re.sub(r'[^a-z0-9]', '', name)
    scoring["name"] = 0
    for n in names:
        n_norm = re.sub(r'[^a-z0-9]+', '_', n).strip('_')
        if n_norm in name_normalized:
            scoring["name"] += 10
            score += 10
            break
        # CamelCase: check all name words appear in separator-stripped URL
        parts = [re.sub(r'[^a-z0-9]', '', p) for p in n.split("_")]
        parts = [p for p in parts if len(p) > 1]
        if (len(parts) >= 2
                and all(p in name_stripped for p in parts)):
            scoring["name"] += 10
            score += 10
            break

    # Try last name only
    if scoring["name"] == 0 and person.last_name:
        if person.last_name.lower() in name:
            scoring["last_name"] = 5
            score += 5

    for good, award in positive_words:
        if good in name:
            if "goodwords" not in scoring:
                scoring["goodwords"] = 0
            scoring["goodwords"] = award
            score += award

    for bad, penalty in negative_words:
        if bad in name:
            if "badnames" not in scoring:
                scoring["badnames"] = 0
            scoring["badnames"] -= penalty
            score -= penalty

    # app.logger.info(f"{filename}: {scoring}")
    return (score, scoring)


def detect_faces(image_bytes: bytes) -> int:
    """Return number of faces detected via OpenCV Haar cascades."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0
    # Cap longest side at 640px — faster, still accurate
    h, w = img.shape[:2]
    scale = min(1.0, 640 / max(h, w))
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    frontal = _face_cascade.detectMultiScale(
        img, scaleFactor=1.1, minNeighbors=8, minSize=(60, 60)
    )
    profile = _profile_cascade.detectMultiScale(
        img, scaleFactor=1.1, minNeighbors=8, minSize=(60, 60)
    )
    all_faces = (list(frontal) if len(frontal) > 0 else []) + \
                (list(profile) if len(profile) > 0 else [])
    if len(all_faces) <= 1:
        return len(all_faces)
    # Merge overlapping boxes — same face detected at multiple scales
    all_faces_doubled = all_faces * 2
    merged, _ = cv2.groupRectangles(all_faces_doubled, 1, eps=0.3)
    return len(merged) if len(merged) > 0 else 1


async def fetch_image_bytes(
    session: aiohttp.ClientSession, url: str
) -> Optional[bytes]:
    try:
        async with session.get(url, headers=HEADERS) as r:
            if r.status == 200:
                return await r.read()
    except Exception:
        pass
    return None


async def throttled_map(items, fn, concurrency=5):
    """Run async function with throttling."""
    results = []
    queue = items.copy()

    async def worker():
        while queue:
            item = queue.pop(0)
            try:
                results.append(await fn(item))
            except Exception:
                pass

    workers = [worker() for _ in range(concurrency)]
    await asyncio.gather(*workers)
    return results


import aiohttp

WIKIDATA_API = "https://www.wikidata.org/w/api.php"


import aiohttp

WIKIDATA_API = "https://www.wikidata.org/w/api.php"


async def find_qid(
    session: aiohttp.ClientSession,
    name: str,
    birth_year: int | None = None,
    death_year: int | None = None,
) -> str | None:

    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": "en",
        "format": "json",
        "limit": 10,
        "type": "item",
        "origin": "*",
    }

    async with session.get(WIKIDATA_API, params=params) as resp:
        if resp.status != 200:
            return None
        data = await resp.json()

    results = data.get("search", [])
    if not results:
        return None

    # If no birth year provided, just return first candidate
    if not birth_year:
        return results[0]["id"]

    # Otherwise verify candidates
    for r in results:
        qid = r["id"]
        if await match_person_years(session, qid, birth_year, death_year):
            return qid

    return None

async def match_person_years(
    session: aiohttp.ClientSession,
    qid: str,
    birth_year: int | None,
    death_year: int | None,
) -> bool:
    """Verify that a Wikidata QID matches the expected birth/death years."""

    if not birth_year:
        return False

    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "claims",
        "format": "json",
        "origin": "*",
    }

    try:
        async with session.get(WIKIDATA_API, params=params) as resp:
            if resp.status != 200:
                return False

            data = await resp.json()

    except Exception:
        return False

    claims = data.get("entities", {}).get(qid, {}).get("claims")
    if not claims:
        return False

    def extract_year(claim_list):
        if not claim_list:
            return None

        try:
            time = (
                claim_list[0]["mainsnak"]["datavalue"]["value"]["time"]
            )
            return int(time[1:5])
        except Exception:
            return None

    if extract_year(claims.get("P569")) != birth_year:
        return False

    if death_year is not None:
        if extract_year(claims.get("P570")) != death_year:
            return False

    return True


# ---------- Fetch functions ----------
HEADERS = {
    "User-Agent": "SF-Bibliografia/1.0 (yp@sf-bibliografia.fi) Python requests"
}


async def fetch_json(session, url, params):
    try:
        async with session.get(url, params=params, headers=HEADERS) as r:
            status = r.status
            if status != 200:
                app.logger.error(f"Fetch returned error: {r.status}")
                return None
            try:
                data = await r.json()
            except Exception as exp:
                app.logger.error(exp)
                data = None
            return data
    except Exception as exp:
        app.logger.error(exp)
        return None


async def fetch_image_meta(session, title: str) -> Optional[WikiImageInfo]:
    """Fetch imageinfo + extmetadata for a file; return only free images."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|descriptionurl|extmetadata|user|dimensions",
        "format": "json",
        "origin": "*",
    }
    try:
        data = await fetch_json(session, COMMONS_API, params)
        if not data or "query" not in data:
            return None
        for page in data["query"]["pages"].values():
            imageinfo = page.get("imageinfo")
            info = None
            if imageinfo:
                info = imageinfo[0]
            if not info:
                continue
            meta = info.get("extmetadata", {})
            # if meta.get("NonFree", {}).get("value") == "true":
            #     continue
            return WikiImageInfo(
                url=info["url"],
                description_url=info.get("descriptionurl"),
                credit=(meta.get("Artist", {}).get("value") or
                        meta.get("Credit", {}).get("value") or
                        info.get("user")),
                license=meta.get("LicenseShortName", {}).get("value"),
                dimensions=info.get("dimensions")
            )
    except Exception:
        return None
    return None


async def fetch_p18(session, qid: str) -> List[str]:
    """Fetch P18 portraits for a QID."""
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "claims",
        "format": "json",
        "origin": "*",
    }
    data = await fetch_json(session, WIKIDATA_API, params)
    if not data:
        return []
    claims = data.get("entities", {}).get(qid, {}).get("claims", {})
    if not claims.get("P18"):
        return []
    return ["File:" + c["mainsnak"]["datavalue"]["value"]
            for c in claims["P18"]]


async def fetch_category_images(session, qid: str) -> List[str]:
    """Fetch images from Commons category linked to Wikidata."""

    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "claims|sitelinks",
        "format": "json",
        "origin": "*",
    }

    data = await fetch_json(session, WIKIDATA_API, params)
    if not data:
        return []

    entity = data.get("entities", {}).get(qid, {})
    claims = entity.get("claims", {})
    sitelinks = entity.get("sitelinks", {})

    category = None

    # 1️⃣ Preferred: Commons sitelink
    commons = sitelinks.get("commonswiki")
    if commons:
        category = commons.get("title")

    # 2️⃣ Fallback: P373 (deprecated but still exists sometimes)
    elif "P373" in claims:
        category = claims["P373"][0]["mainsnak"]["datavalue"]["value"]

    if not category:
        return []

    cat_params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmtype": "file",
        "cmlimit": "200",
        "format": "json",
        "origin": "*",
    }

    cat_data = await fetch_json(session, COMMONS_API, cat_params)
    if not cat_data:
        return []

    return [
        m["title"]
        for m in cat_data.get("query", {}).get("categorymembers", [])
    ]


# async def fetch_category_images(session, qid: str) -> List[str]:
#     """Fetch images from Commons category linked via P373."""
#     params = {
#         "action": "wbgetentities",
#         "ids": qid,
#         "props": "claims|sitelinks",
#         "format": "json",
#         "origin": "*",
#     }
#     data = await fetch_json(session, WIKIDATA_API, params)
#     if not data:
#         return []
#     claims = data.get("entities", {}).get(qid, {}).get("claims", {})
#     if not claims and not claims.get("P373"):
#         return []
#     category = claims["P373"][0]["mainsnak"]["datavalue"]["value"]
#     cat_params = {
#         "action": "query",
#         "list": "categorymembers",
#         "cmtitle": f"Category:{category}",
#         "cmtype": "file",
#         "cmlimit": "200",
#         "format": "json",
#         "origin": "*",
#     }
#     cat_data = await fetch_json(session, COMMONS_API, cat_params)
#     if not cat_data:
#         return []
#     return [m["title"] for m in cat_data.get("query",
#                                              {}).get("categorymembers", [])]


async def fetch_wikipedia_images(session, title: str) -> List[str]:
    """Fetch Wikipedia page images (jpg/png)."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "images",
        "format": "json",
        "origin": "*",
    }
    data = await fetch_json(session, WIKIPEDIA_API, params)
    if not data:
        return []
    pages = data.get("query", {}).get("pages", {})
    images = []
    for page in pages.values():
        for img in page.get("images", []):
            if re.search(r"\.(jpg|jpeg|png)$", img["title"], re.I):
                images.append(img["title"])
    return images


async def search_commons_files(session, name: str) -> List[str]:
    """Search Commons text for image files."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f'"{name}"',
        "srnamespace": "6",
        "srlimit": "50",
        "format": "json",
        "origin": "*",
    }
    data = await fetch_json(session, COMMONS_API, params)
    if not data:
        return []
    return [r["title"] for r in data.get("query", {}).get("search", [])]


# ---------- Main function ----------

async def _fetch_and_score_images(personid: int) -> List[WikiImageInfo]:
    """Fetch, score and sort all free images for a person."""
    async with aiohttp.ClientSession() as session:
        files = []
        psession = new_session()
        person = psession.query(Person).filter(
            Person.id == personid
        ).first()
        # 1️⃣ QID: resolve + verify, then P18 + category
        titles = [n for n in [person.fullname, person.alt_name, person.name]
                  if n]
        qid = person.qid
        if not qid and titles:
            for title in titles:
                qid = await find_qid(
                    session, title, person.dob, person.dod
                )
                if qid:
                    app.logger.info(
                        f'Resolved QID {qid} for person {personid}'
                    )
                    break
        if qid:
            p18_files, cat_files = await asyncio.gather(
                fetch_p18(session, qid),
                fetch_category_images(session, qid)
            )
            app.logger.info(
                f'person {personid}: P18={p18_files} '
                f'category={cat_files}'
            )
            files.extend(p18_files)
            files.extend(cat_files)

        # 2️⃣ Wikipedia page images
        for t in titles:
            wiki_files = await fetch_wikipedia_images(session, t)
            app.logger.info(
                f'person {personid}: wikipedia "{t}"={wiki_files}'
            )
            files.extend(wiki_files)

        # 3️⃣ Commons full-text search
        for t in titles:
            commons_files = await search_commons_files(session, t)
            app.logger.info(
                f'person {personid}: commons search "{t}"={commons_files}'
            )
            files.extend(commons_files)

        # Remove duplicates & keep jpg/png only
        unique_files = list(set(
            {f for f in files
             if re.search(r"\.(jpg|jpeg|png)$", f, re.I)}
        ))

        # Fetch metadata (throttled)
        images: List[Optional[WikiImageInfo]] = await throttled_map(
            unique_files,
            lambda f: fetch_image_meta(session, f),
            concurrency=5
        )

        # Filter out None
        free_images: List[WikiImageInfo] = [i for i in images if i]

        # Scoring (filename heuristics + face detection)
        async def score_with_faces(img: WikiImageInfo) -> WikiImageInfo:
            try:
                img.score, img.scoring = score_image(img.url, person)
                data = await fetch_image_bytes(session, img.url)
                if data:
                    n = detect_faces(data)
                    if n == 1:
                        img.scoring["face"] = 2
                        img.score += 2
                    elif n > 1:
                        img.scoring["face"] = -2
                        img.score -= 2
            except Exception as e:
                app.logger.warning(
                    f"score_with_faces failed for {img.url}: {e}"
                )
            return img

        free_images = await throttled_map(
            free_images, score_with_faces, concurrency=5
        )

        free_images.sort(key=lambda x: x.score, reverse=True)
        app.logger.info(f"Total images found: {len(free_images)}")
        return free_images


async def find_person_images(personid: int, limit: int) -> List[WikiImageInfo]:
    """Return up to limit images for a person, using a 10-min cache."""
    now = datetime.datetime.now()
    cached = _image_cache.get(personid)
    if cached:
        ts, images = cached
        if now - ts < _CACHE_TTL:
            return images[0:limit]

    images = await _fetch_and_score_images(personid)
    _image_cache[personid] = (now, images)
    # Evict all expired entries on each cache write
    expired = [pid for pid, (ts, _) in _image_cache.items()
               if now - ts >= _CACHE_TTL]
    for pid in expired:
        del _image_cache[pid]
    return images[0:limit]


# ---------- Example usage ----------
# async def main():
#     person = PersonImageQuery(
#         name="Cixin Liu",
#         fullname="Cixin Liu",
#         alt_name=None,
#         qid="Q2017"
#     )
#     images = await find_person_images(person)
#     for img in images[:5]:
#         print(img.url, img.license, img.credit)
#
# asyncio.run(main())

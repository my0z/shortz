import os

import requests

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
VALID_EXTENSIONS = {".webm", ".ogv", ".mp4"}


def _search_video_titles(query: str, limit: int) -> list[str]:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"{query} filetype:video",
        "srnamespace": 6,
        "srlimit": limit,
        "format": "json",
    }
    resp = requests.get(COMMONS_API, params=params, timeout=30)
    resp.raise_for_status()
    return [item["title"] for item in resp.json().get("query", {}).get("search", [])]


def _get_file_url(title: str) -> str | None:
    params = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
    }
    resp = requests.get(COMMONS_API, params=params, timeout=30)
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", {})
    for page in pages.values():
        info = page.get("imageinfo")
        if info:
            return info[0].get("url")
    return None


def fetch_topic_videos(query: str, count: int, out_dir: str, max_bytes: int = 20 * 1024 * 1024) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    try:
        titles = _search_video_titles(query, count * 3)
    except Exception:
        return []

    paths = []
    for title in titles:
        if len(paths) >= count:
            break
        try:
            url = _get_file_url(title)
            if not url:
                continue
            ext = os.path.splitext(url)[1].lower()
            if ext not in VALID_EXTENSIONS:
                continue
            head = requests.head(url, timeout=30, allow_redirects=True)
            content_length = int(head.headers.get("content-length", 0))
            if content_length and content_length > max_bytes:
                continue
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            if len(resp.content) > max_bytes:
                continue
            path = os.path.join(out_dir, f"topic_{len(paths)}{ext}")
            with open(path, "wb") as f:
                f.write(resp.content)
            paths.append(path)
        except Exception:
            continue
    return paths

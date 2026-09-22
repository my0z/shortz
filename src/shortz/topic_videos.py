import os

import requests

from .config import config

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
PEXELS_API = "https://api.pexels.com/videos/search"
PIXABAY_API = "https://pixabay.com/api/videos/"
VALID_EXTENSIONS = {".webm", ".ogv", ".mp4"}


def _download(url: str, path: str, max_bytes: int) -> bool:
    try:
        head = requests.head(url, timeout=30, allow_redirects=True)
        content_length = int(head.headers.get("content-length", 0))
        if content_length and content_length > max_bytes:
            return False
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        if len(resp.content) > max_bytes:
            return False
        with open(path, "wb") as f:
            f.write(resp.content)
        return True
    except Exception:
        return False


def _fetch_from_pexels(query: str, count: int, out_dir: str, max_bytes: int) -> list[str]:
    if not config.pexels_api_key:
        return []
    try:
        resp = requests.get(
            PEXELS_API,
            params={"query": query, "per_page": count, "orientation": "portrait"},
            headers={"Authorization": config.pexels_api_key},
            timeout=30,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
    except Exception:
        return []

    paths = []
    for video in videos:
        if len(paths) >= count:
            break
        files = sorted(video.get("video_files", []), key=lambda f: f.get("width") or 9999)
        candidate = next((f for f in files if (f.get("width") or 0) <= 1080), None) or (files[0] if files else None)
        if not candidate or not candidate.get("link"):
            continue
        path = os.path.join(out_dir, f"pexels_{len(paths)}.mp4")
        if _download(candidate["link"], path, max_bytes):
            paths.append(path)
    return paths


def _fetch_from_pixabay(query: str, count: int, out_dir: str, max_bytes: int) -> list[str]:
    if not config.pixabay_api_key:
        return []
    try:
        resp = requests.get(
            PIXABAY_API,
            params={"key": config.pixabay_api_key, "q": query, "per_page": max(count, 3)},
            timeout=30,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except Exception:
        return []

    paths = []
    for hit in hits:
        if len(paths) >= count:
            break
        videos = hit.get("videos", {})
        candidate = videos.get("medium") or videos.get("small") or videos.get("large")
        if not candidate or not candidate.get("url"):
            continue
        path = os.path.join(out_dir, f"pixabay_{len(paths)}.mp4")
        if _download(candidate["url"], path, max_bytes):
            paths.append(path)
    return paths


def _search_commons_titles(query: str, limit: int) -> list[str]:
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


def _get_commons_file_url(title: str) -> str | None:
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


def _fetch_from_commons(query: str, count: int, out_dir: str, max_bytes: int) -> list[str]:
    try:
        titles = _search_commons_titles(query, count * 3)
    except Exception:
        return []

    paths = []
    for title in titles:
        if len(paths) >= count:
            break
        url = _get_commons_file_url(title)
        if not url:
            continue
        ext = os.path.splitext(url)[1].lower()
        if ext not in VALID_EXTENSIONS:
            continue
        path = os.path.join(out_dir, f"commons_{len(paths)}{ext}")
        if _download(url, path, max_bytes):
            paths.append(path)
    return paths


def fetch_topic_videos(query: str, count: int, out_dir: str, max_bytes: int = 20 * 1024 * 1024) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)

    paths = _fetch_from_pexels(query, count, out_dir, max_bytes)
    if len(paths) < count:
        paths += _fetch_from_pixabay(query, count - len(paths), out_dir, max_bytes)
    if len(paths) < count:
        paths += _fetch_from_commons(query, count - len(paths), out_dir, max_bytes)
    return paths

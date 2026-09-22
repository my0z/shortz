import os

import requests

OPENVERSE_API = "https://api.openverse.org/v1/images/"


def fetch_topic_images(query: str, count: int, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    params = {
        "q": query,
        "page_size": count,
        "license_type": "commercial,modification",
        "orientation": "tall",
    }
    try:
        resp = requests.get(OPENVERSE_API, params=params, timeout=30)
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except Exception:
        return []

    paths = []
    for i, item in enumerate(results[:count]):
        url = item.get("url") or item.get("thumbnail")
        if not url:
            continue
        try:
            img_resp = requests.get(url, timeout=30)
            img_resp.raise_for_status()
        except Exception:
            continue
        path = os.path.join(out_dir, f"topic_{i}.jpg")
        with open(path, "wb") as f:
            f.write(img_resp.content)
        paths.append(path)
    return paths

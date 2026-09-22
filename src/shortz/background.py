import os
import random

import requests

from .config import config


def fetch_random_background(out_path: str) -> str:
    seed = random.randint(1, 100000)
    url = f"https://picsum.photos/seed/{seed}/{config.width}/{config.height}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(response.content)
    return out_path


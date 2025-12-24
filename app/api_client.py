import requests
from .config import get_settings
from typing import List, Dict, Any

settings = get_settings()


def fetch_api_items(since: str = None) -> List[Dict[str, Any]]:
    headers = {}
    if settings.API_KEY:
        headers['Authorization'] = f'Bearer {settings.API_KEY}'
    params = {}
    if since:
        params['since'] = since
    resp = requests.get(settings.API_URL, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get('items', resp.json())

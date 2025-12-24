"""Client for the second API source.

This is intentionally small — it expects the second API to return JSON
with a top-level `results` array containing objects with at least
`uid` and `fullName` fields. The test will monkeypatch this function.
"""
import requests
from .config import get_settings

settings = get_settings()


def fetch_api2_items(since: str = None):
    url = settings.SECOND_API_URL
    headers = {}
    if settings.SECOND_API_KEY:
        headers['Authorization'] = f"Bearer {settings.SECOND_API_KEY}"
    params = {}
    if since:
        params['since'] = since
    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    # normalize fallback — accept top-level list or {results: [...]}
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    if isinstance(data, list):
        return data
    return []

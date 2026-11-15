"""
HTTP client for blackbox testing of the LocalFM service.
"""

from typing import Any, Optional

import httpx


class BlackboxClient:
    """
    HTTP client targeting a running LocalFM service instance.
    Wraps httpx.Client to provide intuitive request helpers.
    """

    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    @property
    def client(self) -> httpx.Client:
        return self._client

    def _normalize_path(self, path: str) -> str:
        if not path.startswith("/"):
            return "/" + path
        return path

    def get(self, path: str, **kwargs) -> httpx.Response:
        return self._client.get(self._normalize_path(path), **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        return self._client.post(self._normalize_path(path), **kwargs)

    def put(self, path: str, **kwargs) -> httpx.Response:
        return self._client.put(self._normalize_path(path), **kwargs)

    def delete(self, path: str, **kwargs) -> httpx.Response:
        return self._client.delete(self._normalize_path(path), **kwargs)

    def get_json(self, path: str, **kwargs) -> Any:
        res = self.get(path, **kwargs)
        res.raise_for_status()
        return res.json()

    def post_json(self, path: str, json_data: Any = None, **kwargs) -> Any:
        res = self.post(path, json=json_data, **kwargs)
        res.raise_for_status()
        return res.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "BlackboxClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<BlackboxClient base_url='{self.base_url}'>"

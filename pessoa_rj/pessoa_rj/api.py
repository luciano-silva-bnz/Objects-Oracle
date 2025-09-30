from __future__ import annotations

from typing import Any, Tuple

import requests
from requests import Session

from .config import API_AUTH_URL, API_COMPANY_ID, API_TOKEN_URL, API_URL_BASE
from .logging_config import get_logger
from .token_store import load_refresh_token, save_tokens

logger = get_logger(__name__)


def _request_token(username: str, password: str) -> dict[str, Any]:
    payload = {
        "company": int(API_COMPANY_ID),
        "username": username,
        "password": password,
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(API_AUTH_URL, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    save_tokens(data)
    return data


def _refresh_token(refresh_token: str) -> dict[str, Any] | None:
    payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(API_TOKEN_URL, data=payload, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        logger.warning("Falha ao renovar token de acesso")
        return None
    data = response.json()
    save_tokens(data)
    return data


class TotvsAPI:
    """Cliente para comunicacao com a API TOTVS Consinco."""

    def __init__(self, session: Session | None = None) -> None:
        self.session: Session = session or Session()
        self.access_token: str | None = None
        self.refresh_token: str | None = load_refresh_token()

    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        try:
            data = _request_token(username, password)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Falha ao autenticar usuario %s", username)
            return False, str(exc)
        self.access_token = data.get("accessToken") or data.get("access_token")
        self.refresh_token = data.get("refreshToken") or data.get("refresh_token")
        logger.info("Autenticacao bem-sucedida para %s", username)
        return True, ""

    def autenticar(self, username: str, password: str) -> Tuple[bool, str]:
        return self.authenticate(username, password)

    def _ensure_token(self) -> bool:
        if self.access_token:
            return True
        if self.refresh_token:
            data = _refresh_token(self.refresh_token)
            if data:
                self.access_token = data.get("accessToken") or data.get("access_token")
                self.refresh_token = data.get("refreshToken") or data.get("refresh_token")
        return bool(self.access_token)

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        if not self._ensure_token():
            raise RuntimeError("Token de acesso invalido")
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        response = self.session.request(method, url, headers=headers, **kwargs)
        if response.status_code == 401 and self.refresh_token:
            data = _refresh_token(self.refresh_token)
            if data:
                self.access_token = data.get("accessToken") or data.get("access_token")
                self.refresh_token = data.get("refreshToken") or data.get("refresh_token")
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = self.session.request(method, url, headers=headers, **kwargs)
        return response

    def consultar_pessoa(self, numero: str, digito: str) -> tuple[int | None, str | None]:
        if not self._ensure_token():
            return None, None
        params = {"numeroCPFCNPJ": numero, "digitoCPFCNPJ": digito}
        response = self._request("GET", API_URL_BASE, params=params, timeout=30)
        if response.status_code == 200:
            items = response.json().get("items", [])
            if items:
                first = items[0]
                return first.get("idPessoa"), first.get("status")
        return None, None

    def incluir_pessoa(self, payload: dict[str, Any]) -> requests.Response:
        return self._request("POST", API_URL_BASE, json=payload, timeout=30)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


def _resolve_package_dir() -> Path:
    return Path(__file__).resolve().parent


def _resolve_runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _resolve_package_dir().parent


PACKAGE_DIR: Path = _resolve_package_dir()
RUNTIME_DIR: Path = _resolve_runtime_dir()
ASSETS_DIR: Path = PACKAGE_DIR / "assets"
QUERIES_DIR: Path = PACKAGE_DIR / "queries"
LOG_FILE: Path = RUNTIME_DIR / "pessoa_rj.log"
TOKEN_STORAGE_FILE: Path = RUNTIME_DIR / "token_storage.json"

API_AUTH_URL = "https://bonanza150976.consinco.cloudtotvs.com.br:8343/api/v1/auth/login"
API_TOKEN_URL = "https://bonanza150976.consinco.cloudtotvs.com.br:8343/api/v1/auth/token"
API_COMPANY_ID = "1"
API_URL_BASE = "https://bonanza150976.consinco.cloudtotvs.com.br:8343/CadastrosEstruturaisAPI/api/v1/Pessoa"


@dataclass(frozen=True)
class DatabaseConfig:
    name: str
    user: str
    password: str
    dsn: str
    query_file: Path


DATABASES: tuple[DatabaseConfig, ...] = (
    DatabaseConfig(
        name="BNZ",
        user="BonanzaPRDREAD",
        password="eajsy84153NWYJU@!",
        dsn="45.6.153.115:2070/C1PCXH_180377_P_high.paas.oracle.com",
        query_file=QUERIES_DIR / "bnz.sql",
    ),
    DatabaseConfig(
        name="MLT",
        user="MultiPRDREAD",
        password="fmglw49538EIRWK?!",
        dsn="45.6.153.115:2020/C1PCXH_180376_P_high.paas.oracle.com",
        query_file=QUERIES_DIR / "mlt.sql",
    ),
    DatabaseConfig(
        name="ALI",
        user="AliancaPRDREAD",
        password="nrvkj02374WZTIE!@",
        dsn="45.6.153.115:2120/C1PCXH_180375_P_medium.paas.oracle.com",
        query_file=QUERIES_DIR / "ali.sql",
    ),
)

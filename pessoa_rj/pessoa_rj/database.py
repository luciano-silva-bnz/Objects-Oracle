from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd

from .config import DATABASES, DatabaseConfig
from .logging_config import get_logger

logger = get_logger(__name__)


def build_in_clause(cpfs: Sequence[str]) -> str:
    quoted = [f"'{cpf}'" for cpf in cpfs if cpf]
    if not quoted:
        raise ValueError("Lista de CPFs vazia para montar IN clause")
    return f"r.ra_cic IN ({','.join(quoted)})"


def _load_query(config: DatabaseConfig) -> str:
    return config.query_file.read_text(encoding="utf-8")


def execute_query(config: DatabaseConfig, cpfs: Sequence[str]) -> pd.DataFrame:
    import oracledb  # import local para evitar dependência se não for usado

    query_template = _load_query(config)
    clause = build_in_clause(cpfs)
    query = query_template.format(in_clause=clause)

    logger.info("Consultando banco %s", config.name)
    conn = oracledb.connect(user=config.user, password=config.password, dsn=config.dsn)
    try:
        df = pd.read_sql(query, conn)
    finally:
        conn.close()

    df['BANCO_ORIGEM'] = config.name
    return df


def fetch_from_all(cpfs: Sequence[str]) -> list[pd.DataFrame]:
    resultados: list[pd.DataFrame] = []
    for config in DATABASES:
        df = execute_query(config, cpfs)
        resultados.append(df)
    return resultados

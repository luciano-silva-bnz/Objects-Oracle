from __future__ import annotations

APP_NAME = "Cadastro de Pessoas(F) Consinco"
COMPANY_NAME = "Bonanza Supermercados"
APP_VERSION = "2.2.0"
APP_VERSION_TUPLE = (2, 2, 0, 0)
EXECUTABLE_NAME = "cadastro_pessoa_gui.exe"
COPYRIGHT = "Bonanza Supermercados"

__version__ = APP_VERSION


def get_main_window_title() -> str:
    return f"{APP_NAME} V.{APP_VERSION} - {COMPANY_NAME}"


def get_tool_window_title(base_title: str) -> str:
    return f"{base_title} - v{APP_VERSION}"


def get_about_text(runtime_path: str | None = None) -> str:
    linhas = [
        APP_NAME,
        f"Versao: {APP_VERSION}",
        f"Empresa: {COMPANY_NAME}",
        "",
        "Como atualizar:",
        "1. Feche o sistema.",
        "2. Substitua o executavel antigo pelo novo.",
        "3. Mantenha o mesmo atalho ou a mesma pasta de instalacao.",
    ]
    if runtime_path:
        linhas.extend(["", f"Executavel: {runtime_path}"])
    return "\n".join(linhas)

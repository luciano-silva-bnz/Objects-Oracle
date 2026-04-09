from __future__ import annotations

import importlib
import sys
from typing import Any

from .logging_config import get_logger
from .ui.app import run_app

logger = get_logger(__name__)


def _run_auxiliary(module_name: str) -> None:
    module = importlib.import_module(module_name)
    exit_code: Any = 0
    if hasattr(module, "main") and callable(module.main):  # type: ignore[attr-defined]
        exit_code = module.main()  # type: ignore[call-arg]
    sys.exit(int(exit_code) if isinstance(exit_code, int) else 0)


def main() -> None:
    if "--run-convert" in sys.argv:
        sys.argv = [arg for arg in sys.argv if arg != "--run-convert"]
        _run_auxiliary("pessoa_rj.tools.convert")
        return
    if "--run-comprov" in sys.argv:
        sys.argv = [arg for arg in sys.argv if arg != "--run-comprov"]
        _run_auxiliary("pessoa_rj.tools.comprov")
        return
    if "--run-fgts" in sys.argv:
        sys.argv = [arg for arg in sys.argv if arg != "--run-fgts"]
        _run_auxiliary("pessoa_rj.tools.gerar_planilha_fgts")
        return
    run_app()


if __name__ == "__main__":
    main()

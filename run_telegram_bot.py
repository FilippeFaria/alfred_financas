from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
VENV_SITE_PACKAGES = ROOT / ".venv" / "Lib" / "site-packages"


def preparar_path() -> None:
    # Reaproveita os pacotes puros da .venv e preserva pandas/numpy do runtime atual.
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))
    if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
        sys.path.append(str(VENV_SITE_PACKAGES))


if __name__ == "__main__":
    preparar_path()
    from src.telegram_bot.bot import main

    main()

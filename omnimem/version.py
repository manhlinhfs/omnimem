from importlib import metadata
from pathlib import Path

# `VERSION` lives at the repo root. Walk two `.parent`s
# (version.py → omnimem/ → repo root) after the v1.3.0 package refactor.
ROOT_DIR = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT_DIR / "VERSION"


def get_version():
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()

    try:
        return metadata.version("omnimem")
    except metadata.PackageNotFoundError:
        return "0.0.0+unknown"


def get_version_banner():
    return f"OmniMem v{get_version()}"


def add_version_argument(parser):
    parser.add_argument(
        "--version",
        action="version",
        version=get_version_banner(),
        help="Show the OmniMem version and exit",
    )

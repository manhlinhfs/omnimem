from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
VERSION_FILE = ROOT_DIR / "VERSION"


def get_version():
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def get_version_banner():
    return f"OmniMem v{get_version()}"


def add_version_argument(parser):
    parser.add_argument(
        "--version",
        action="version",
        version=get_version_banner(),
        help="Show the OmniMem version and exit",
    )

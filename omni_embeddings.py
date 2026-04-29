import os
import shutil
from pathlib import Path

from omni_config import get_allow_model_download
from omni_paths import SOURCE_ROOT, get_bootstrap_command, get_models_root

MODEL_REPO_ID = os.getenv(
    "OMNIMEM_EMBED_MODEL_REPO", "sentence-transformers/all-MiniLM-L6-v2"
)
REQUIRED_MODEL_FILES = (
    "config.json",
    "modules.json",
    "model.safetensors",
    "tokenizer.json",
)


def _env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_model_dir():
    override = os.getenv("OMNIMEM_MODEL_DIR")
    if override:
        return Path(override).expanduser()
    return get_models_root() / MODEL_REPO_ID.split("/")[-1]


def is_model_bootstrapped(model_dir=None):
    candidate = Path(model_dir) if model_dir else get_model_dir()
    return candidate.is_dir() and all((candidate / name).exists() for name in REQUIRED_MODEL_FILES)


def bootstrap_model(local_files_only=False, force=False):
    from huggingface_hub import snapshot_download

    model_dir = get_model_dir()
    if is_model_bootstrapped(model_dir) and not force:
        return model_dir

    model_dir.parent.mkdir(parents=True, exist_ok=True)

    try:
        snapshot_path = snapshot_download(
            repo_id=MODEL_REPO_ID,
            local_files_only=local_files_only,
            force_download=force and not local_files_only,
            token=os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN"),
            etag_timeout=30,
            max_workers=4,
        )
        shutil.copytree(snapshot_path, model_dir, dirs_exist_ok=True)
    except Exception as exc:
        if local_files_only:
            raise RuntimeError(
                f"Embedding model is not bootstrapped at '{model_dir}' and could not be restored "
                "from the local Hugging Face cache. Run "
                f"`{get_bootstrap_command(root_dir=SOURCE_ROOT)}` once while online."
            ) from exc
        raise RuntimeError(
            f"Failed to download the embedding model '{MODEL_REPO_ID}' into '{model_dir}'. "
            "Check network access or set HF_TOKEN for private/rate-limited environments."
        ) from exc

    if not is_model_bootstrapped(model_dir):
        raise RuntimeError(
            f"Embedding model bootstrap finished, but '{model_dir}' is missing required files."
        )

    return model_dir


def ensure_model_ready():
    model_dir = get_model_dir()
    if is_model_bootstrapped(model_dir):
        return model_dir

    try:
        return bootstrap_model(local_files_only=True)
    except RuntimeError:
        if get_allow_model_download(root_dir=SOURCE_ROOT) or _env_flag(
            "OMNIMEM_ALLOW_MODEL_DOWNLOAD",
            default=False,
        ):
            return bootstrap_model(local_files_only=False)
        raise RuntimeError(
            f"Embedding model is not ready at '{model_dir}'. Run "
            f"`{get_bootstrap_command(root_dir=SOURCE_ROOT)}` once while online, "
            "or set OMNIMEM_ALLOW_MODEL_DOWNLOAD=1 to let runtime download it."
        )


def build_embedding_function():
    from chromadb.utils import embedding_functions

    model_dir = ensure_model_ready()

    # Runtime should stay offline-safe after the model has been bootstrapped.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=str(model_dir))

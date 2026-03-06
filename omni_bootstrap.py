import argparse
import sys

from omni_embeddings import MODEL_REPO_ID, bootstrap_model, get_model_dir


def main():
    parser = argparse.ArgumentParser(
        description="Download or restore OmniMem's embedding model into a local directory"
    )
    parser.add_argument(
        "--offline-only",
        action="store_true",
        help="Only restore from local Hugging Face cache, never hit the network",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download the model into the local OmniMem directory",
    )
    args = parser.parse_args()

    print(f"[OmniMem] Model repo: {MODEL_REPO_ID}")
    print(f"[OmniMem] Local model dir: {get_model_dir()}")

    try:
        model_dir = bootstrap_model(local_files_only=args.offline_only, force=args.force)
    except RuntimeError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    print(f"[OmniMem] Model is ready at: {model_dir}")


if __name__ == "__main__":
    main()

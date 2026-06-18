import argparse
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_TARGETS = [
    PROJECT_ROOT / "mineru_runtime",
    PROJECT_ROOT / "logs",
    PROJECT_ROOT / "cache" / "vector_store",
]


def clean_path(path, dry_run=True):
    if not path.exists():
        return {"path": str(path), "exists": False, "removed": False}

    if dry_run:
        return {"path": str(path), "exists": True, "removed": False}

    if path.is_dir():
        shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
    else:
        path.unlink()

    return {"path": str(path), "exists": True, "removed": True}


def main():
    parser = argparse.ArgumentParser(
        description="Clean Math-learning-agent runtime directories.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually clean files. Default is dry-run.",
    )
    args = parser.parse_args()

    dry_run = not args.apply

    for target in RUNTIME_TARGETS:
        result = clean_path(target, dry_run=dry_run)
        action = "would clean" if dry_run else "cleaned"

        if not result["exists"]:
            action = "missing"

        print(f"[{action}] {result['path']}")


if __name__ == "__main__":
    main()

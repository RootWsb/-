#!/usr/bin/env python3
"""Download the embedding model from ModelScope for offline transformer loading."""

from __future__ import annotations

import argparse
import inspect
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download an embedding model from ModelScope to a local directory."
    )
    parser.add_argument(
        "--model-id",
        default="Qwen/Qwen3-Embedding-0.6B",
        help="ModelScope model id.",
    )
    parser.add_argument(
        "--output-dir",
        default="models/Qwen3-Embedding-0.6B",
        help="Local directory used by --embedding-model.",
    )
    parser.add_argument(
        "--revision",
        default=None,
        help="Optional ModelScope revision.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from modelscope import snapshot_download
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: modelscope. Install it with "
            "`python -m pip install modelscope` or reinstall requirements-training.txt."
        ) from exc

    kwargs = {
        "model_id": args.model_id,
        "revision": args.revision,
    }
    signature = inspect.signature(snapshot_download)
    if "local_dir" in signature.parameters:
        kwargs["local_dir"] = str(output_dir)
    else:
        kwargs["cache_dir"] = str(output_dir.parent)

    kwargs = {key: value for key, value in kwargs.items() if value is not None}
    downloaded_path = Path(snapshot_download(**kwargs)).resolve()

    print(f"model_id: {args.model_id}")
    print(f"downloaded_path: {downloaded_path}")
    print(f"embedding_model_arg: {downloaded_path}")
    print()
    print("Train with:")
    print(
        "python skill_router_training/core/train.py "
        "--data skill_router_training/data_prod/training_data_mixed_1000.jsonl "
        "--output skill_router_training/checkpoints/skill_router_prod_synth_1000 "
        "--epochs 50 --batch-size 50 --lr 0.0001 --device cuda "
        f"--embedding-model {downloaded_path} --local-files-only"
    )


if __name__ == "__main__":
    main()

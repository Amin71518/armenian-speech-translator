"""Prepare NLLB separately from offline inference measurements."""

import argparse
import json
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

from armenian_speech.translation import DEFAULT_TRANSLATION_MODEL, NLLB_REVISION


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--revision", default=NLLB_REVISION, help="Pin an upstream model commit")
    args = cli.parse_args()
    repo = DEFAULT_TRANSLATION_MODEL
    revision = args.revision
    files = {item.rfilename for item in HfApi().model_info(repo, revision=revision).siblings}
    weights = "model.safetensors" if "model.safetensors" in files else "pytorch_model.bin"
    snapshot = Path(snapshot_download(
        repo, cache_dir=".cache/models/translation", revision=revision,
        allow_patterns=["*.json", "*.model", weights], max_workers=1,
    ))
    print(json.dumps({"repo": repo, "revision": snapshot.name, "weights": weights}), flush=True)


if __name__ == "__main__":
    main()

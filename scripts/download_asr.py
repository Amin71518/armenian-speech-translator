"""Download only Vana-Labs INT8 artifacts at a resolved, recorded model revision."""

import argparse
import hashlib
import json
from pathlib import Path

from huggingface_hub import snapshot_download

REPO = "Vana-Labs/stt-fastconformer-armenian"
REVISION = "ec92cef52199c3874681321b13853e8fe602d23f"
FILES = [
    "encoder-model.int8.onnx", "decoder_joint-model.int8.onnx",
    "nemo80.onnx", "config.json", "vocab.txt", "README.md",
]


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--revision", default=REVISION)
    revision = cli.parse_args().revision
    directory = Path(".cache/models/vana")
    snapshot_download(REPO, revision=revision, local_dir=directory, allow_patterns=FILES)
    hashes = {}
    for name in FILES:
        with (directory / name).open("rb") as stream:
            hashes[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    provenance = {"repo": REPO, "revision": revision, "sha256": hashes}
    (directory / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()

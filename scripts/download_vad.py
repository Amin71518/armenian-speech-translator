"""Prepare the pinned Silero ONNX artifact; never install or execute its wheel."""

import argparse
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

from armenian_speech.vad import MODEL_SHA256, VAD_VERSION, WHEEL_SHA256

WHEEL_URL = (
    "https://files.pythonhosted.org/packages/84/ef/"
    "9099037ed6f180ea33220178df4107112c0ce2bf5fb4d6f6ab19db2844ed/"
    "silero_vad-6.2.3-py3-none-any.whl"
)


def prepare(directory: Path) -> dict:
    with urllib.request.urlopen(WHEEL_URL, timeout=60) as response:
        wheel = response.read()
    if hashlib.sha256(wheel).hexdigest() != WHEEL_SHA256:
        raise ValueError("Silero wheel checksum mismatch.")
    with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
        model = archive.read("silero_vad/data/silero_vad.onnx")
        license_text = archive.read(f"silero_vad-{VAD_VERSION}.dist-info/licenses/LICENSE")
    if hashlib.sha256(model).hexdigest() != MODEL_SHA256:
        raise ValueError("Silero model checksum mismatch.")
    provenance = {
        "distribution": "silero-vad", "version": VAD_VERSION, "wheel_url": WHEEL_URL,
        "wheel_sha256": WHEEL_SHA256, "model_sha256": MODEL_SHA256, "license": "MIT",
    }
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "silero_vad.onnx").write_bytes(model)
    (directory / "LICENSE").write_bytes(license_text)
    (directory / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return provenance


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--directory", type=Path, default=Path(".cache/models/silero"))
    args = cli.parse_args()
    print(json.dumps(prepare(args.directory), indent=2))


if __name__ == "__main__":
    main()

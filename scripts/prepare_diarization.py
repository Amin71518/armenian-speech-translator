"""Prepare public, checksum-pinned speaker models and a small labelled LibriSpeech subset."""

import argparse
import hashlib
import io
import json
import tarfile
import urllib.request
import wave
from collections import Counter
from pathlib import Path

from scripts.prepare_samples import pcm_wav

RELEASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models"
MODELS = {
    "campplus": (
        "3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx",
        "aa3cfc16963a10586a9393f5035d6d6b57e98d358b347f80c2a30bf4f00ceba2",
    ),
    "titanet": (
        "nemo_en_titanet_small.onnx",
        "ad4a1802485d8b34c722d2a9d04249662f2ece5d28a7a039063ca22f515a789e",
    ),
}
CORPUS_URL = "https://www.openslr.org/resources/12/test-clean.tar.gz"


def fetch(url):
    return urllib.request.urlopen(url, timeout=60)


def prepare_models(directory):
    for name, (filename, digest) in MODELS.items():
        destination = directory / name
        path = destination / "model.onnx"
        if path.exists():
            data = path.read_bytes()
        else:
            with fetch(f"{RELEASE}/{filename}") as response:
                data = response.read()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Model checksum mismatch: {name}")
        destination.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        (destination / "PROVENANCE.json").write_text(json.dumps({
            "url": f"{RELEASE}/{filename}", "sha256": digest,
            "checksum_source": f"{RELEASE}/checksum.txt", "runtime": "sherpa-onnx==2.0.1",
        }, indent=2), encoding="utf-8")
        print(f"Prepared {name}: {len(data)} bytes", flush=True)


def prepare_data(directory):
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Data directory must be empty; existing fixtures are never overwritten")
    directory.mkdir(parents=True, exist_ok=True)
    counts, rows = Counter(), []
    # Stream and stop after six >=4.5 s utterances for each of the first three speakers.
    # Only selected FLAC bytes are decoded; no archive paths are extracted.
    with fetch(CORPUS_URL) as response, tarfile.open(fileobj=response, mode="r|gz") as archive:
        for member in archive:
            path = Path(member.name)
            if not member.isfile() or path.suffix != ".flac":
                continue
            speaker = path.stem.split("-")[0]
            if speaker not in counts and len(counts) >= 3:
                continue
            if counts[speaker] >= 6:
                continue
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Missing archive member")
            source = stream.read()
            data = pcm_wav(source)
            with wave.open(io.BytesIO(data), "rb") as audio:
                duration = audio.getnframes() / audio.getframerate()
            if duration < 4.5:
                continue
            filename = path.stem + ".wav"
            (directory / filename).write_bytes(data)
            rows.append({
                "audio": filename, "speaker": speaker, "duration_s": duration,
                "split": "calibration" if counts[speaker] < 2 else "evaluation",
                "sha256": hashlib.sha256(data).hexdigest(),
                "source_sha256": hashlib.sha256(source).hexdigest(),
                "source_member": member.name, "source": CORPUS_URL,
                "license": "CC-BY-4.0", "attribution": "Panayotov et al., LibriSpeech, SLR12",
                "integrity_scope": "Individual member hashes; full streamed archive not verified",
            })
            counts[speaker] += 1
            print(f"Prepared speaker {speaker}: {counts[speaker]}/6", flush=True)
            if len(counts) == 3 and min(counts.values()) == 6:
                break
    if len(rows) != 18:
        raise ValueError(f"Incomplete subset: {dict(counts)}")
    (directory / "manifest.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8",
    )


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--models", action="store_true")
    cli.add_argument("--data", action="store_true")
    args = cli.parse_args()
    if not args.models and not args.data:
        cli.error("Select --models and/or --data explicitly")
    if args.models:
        prepare_models(Path(".cache/models/speakers"))
    if args.data:
        prepare_data(Path("data/local/diarization"))


if __name__ == "__main__":
    main()

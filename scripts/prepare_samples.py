"""Download a small public FLEURS Armenian test subset, not the whole corpus."""

import argparse
import csv
import hashlib
import io
import json
import sys
import tarfile
import urllib.request
import wave
from pathlib import Path

DATASET = "google/fleurs"
SOURCE = "https://huggingface.co/datasets/google/fleurs"
REVISION = "70bb2e84b976b7e960aa89f1c648e09c59f894dd"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "armenian-speech-stage1/0.1"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def pcm_wav(data: bytes) -> bytes:
    """Normalize source float WAVs to mono 16 kHz PCM16 using the project decoder."""
    import av

    output = io.BytesIO()
    with av.open(io.BytesIO(data)) as container, wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16_000)
        for source_frame in container.decode(audio=0):
            for frame in resampler.resample(source_frame):
                wav.writeframes(frame.to_ndarray().tobytes())
        for frame in resampler.resample(None):
            wav.writeframes(frame.to_ndarray().tobytes())
    return output.getvalue()


def prepare(output: Path, count: int) -> None:
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Output directory is not empty: {output}; use a new directory")
    base = f"{SOURCE}/resolve/{REVISION}/data"
    annotations = list(csv.reader(
        io.StringIO(fetch(f"{base}/hy_am/test.tsv").decode("utf-8")), delimiter="\t",
    ))
    # Original TSV: id, filename, raw text, normalized text, characters, samples, gender.
    if not annotations or any(len(row) != 7 for row in annotations):
        raise ValueError("Unexpected FLEURS annotation schema")
    by_filename = {row[1]: row for row in annotations}
    english = {}
    for row in csv.reader(
        io.StringIO(fetch(f"{base}/en_us/test.tsv").decode("utf-8")), delimiter="\t",
    ):
        english.setdefault(row[0], row[2])
    output.mkdir(parents=True, exist_ok=True)
    manifest, seen = [], set()
    request = urllib.request.Request(
        f"{base}/hy_am/audio/test.tar.gz", headers={"User-Agent": "armenian-speech-stage1/0.1"},
    )
    print(f"Streaming original FLEURS test archive at revision {REVISION}", flush=True)
    with urllib.request.urlopen(request, timeout=90) as response:
        # Stream the archive and stop after enough samples; never extract archive paths.
        with tarfile.open(fileobj=response, mode="r|gz") as archive:
            for member in archive:
                row = by_filename.get(Path(member.name).name)
                if not member.isfile() or row is None or row[0] in seen:
                    continue
                if not 3 <= int(row[5]) / 16_000 <= 15 or not row[3].strip():
                    continue
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"Cannot read archive member: {member.name}")
                source_data = stream.read()
                data = pcm_wav(source_data)
                with wave.open(io.BytesIO(data), "rb") as wav:
                    rate = wav.getframerate()
                    duration = wav.getnframes() / rate
                    if wav.getnchannels() != 1 or rate != 16_000 or not 3 <= duration <= 15:
                        raise ValueError(f"Unexpected audio format/duration: {member.name}")
                seen.add(row[0])
                path = output / f"{len(manifest) + 1:03d}.wav"
                path.write_bytes(data)
                manifest.append({
                    "audio": path.name,
                    "reference_hy": row[3],
                    "reference_en": english.get(row[0]),
                    "source": SOURCE,
                    "source_file": row[1],
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "source_sha256": hashlib.sha256(source_data).hexdigest(),
                    "dataset": DATASET,
                    "config": "hy_am",
                    "split": "test",
                    "utterance_id": row[0],
                    "license": "CC-BY-4.0",
                    "dataset_revision": REVISION,
                    "duration_s": duration,
                })
                print(f"Downloaded {len(manifest)}/{count}: {path.name} ({duration:.2f}s)",
                      flush=True)
                if len(manifest) == count:
                    break
    if len(manifest) != count:
        raise ValueError(f"Only {len(manifest)} suitable unique samples in test archive")
    manifest_path = output / "manifest.jsonl"
    manifest_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest), encoding="utf-8",
    )
    print(f"Manifest: {manifest_path}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, default=Path("data/local/fleurs"))
    cli.add_argument("--count", type=int, default=15)
    cli.add_argument("--inspect-source", action="store_true", help="Inspect upstream data files")
    args = cli.parse_args()
    if not 1 <= args.count <= 15:
        cli.error("count must be between 1 and 15")
    try:
        if args.inspect_source:
            metadata = json.loads(fetch(f"https://huggingface.co/api/datasets/{DATASET}"))
            print("Revision:", metadata["sha"])
            for item in metadata["siblings"]:
                if "hy_am" in item["rfilename"]:
                    print(item["rfilename"])
            url = f"{SOURCE}/resolve/{metadata['sha']}/data/hy_am/test.tsv"
            print("First annotation:", fetch(url).decode("utf-8").splitlines()[0])
            return 0
        prepare(args.output, args.count)
    except (OSError, ValueError, KeyError, wave.Error) as error:
        print(f"Preparation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

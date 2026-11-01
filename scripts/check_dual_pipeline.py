"""Two concurrent file streams through independent VADs and one real worker; not live latency."""

import hashlib
import json
import sys
import wave
from pathlib import Path
from time import perf_counter, sleep

from armenian_speech.fair_queue import FairQueue
from armenian_speech.latency import numeric_result
from armenian_speech.live_pipeline import InferenceWorker, WorkerConfig
from armenian_speech.live_vad import LiveVAD
from armenian_speech.microphone import AudioBlock
from armenian_speech.vad import SileroVAD


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    manifest = [json.loads(line) for line in Path('data/local/fleurs/manifest.jsonl')
                .read_text(encoding="utf-8").splitlines() if line.strip()]
    pcm = {}
    for label, name in (("Me", "001.wav"), ("System", "004.wav")):
        row = next(row for row in manifest if row["audio"] == name)
        path = Path("data/local/fleurs") / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Fixture checksum mismatch.")
        with wave.open(str(path), "rb") as audio:
            pcm[label] = b"\0\0" * 16000 + audio.readframes(audio.getnframes()) + b"\0\0" * 16000
    vad = {label: LiveVAD(SileroVAD(Path(".cache/models/silero")), 16000, 1) for label in pcm}
    events = []
    worker = InferenceWorker(WorkerConfig(Path(".cache/models")),
                             on_result=lambda event: events.append(numeric_result(event)))
    queue = FairQueue(worker)
    failure = None
    try:
        worker.start()
        started = perf_counter()
        for offset in range(0, max(len(data) // 2 for data in pcm.values()), 320):
            due = started + (offset + 320) / 16000
            while perf_counter() < due:
                queue.dispatch()
                sleep(min(0.005, max(0, due - perf_counter())))
            for label, data in pcm.items():
                block = data[offset * 2:(offset + 320) * 2]
                if block:
                    for segment in vad[label].push(AudioBlock(
                        block, len(block) // 2, offset, offset / 16000, offset / 16000,
                    )):
                        queue.offer(label, segment)
            queue.dispatch()
        for label in pcm:
            for segment in vad[label].finish("eof"):
                queue.offer(label, segment)
        deadline = perf_counter() + 15
        while queue.pending:
            queue.dispatch()
            if perf_counter() > deadline:
                raise RuntimeError("Replay drain timeout.")
            sleep(0.005)
        worker.shutdown_timeout = max(0.001, deadline - perf_counter())
        worker.close()
    except Exception as error:
        failure = str(error)
    finally:
        queue.cancel()
        worker.close(drain=False)
    report = {"scope": "Two nominal-rate file streams; not physical microphone or E2E latency",
              "scheduler": queue.summary(), "inference": worker.summary(), "results": events,
              "vad": {label: value.stats for label, value in vad.items()}, "error": failure}
    Path("reports/stage33_dual_replay.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8",
    )
    print(json.dumps({"scheduler": queue.summary(), "inference": worker.summary()}, indent=2))
    if failure:
        raise RuntimeError(failure)
    assert all(worker.summary()["sources"][label]["completed"] >= 1 for label in pcm)


if __name__ == "__main__":
    main()

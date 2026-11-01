"""Real spawned System diarization/ASR/MT smoke on public clips; not Armenian speaker DER."""

import json
import struct
import sys
from dataclasses import replace
from pathlib import Path
from time import perf_counter, sleep

from armenian_speech.latency import numeric_result
from armenian_speech.live_pipeline import InferenceWorker, WorkerConfig
from armenian_speech.vad import SpeechSegment
from scripts.check_speakers import read_rows


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = read_rows()
    speakers = list(dict.fromkeys(row["speaker"] for row in rows))[:2]
    clips = [next(row["pcm"][:32000] for row in rows if row["speaker"] == speaker
                  and row["split"] == "evaluation") for speaker in speakers]
    pcm = [(clip * 32768).astype("<i2").tobytes() for clip in clips]
    events = []
    worker = InferenceWorker(WorkerConfig(Path(".cache/models"), diarize_system=True),
                             on_result=lambda event: events.append(numeric_result(event)))
    started = perf_counter()

    def segment(data, start=0):
        return SpeechSegment(data, start, start + len(data) // 2, start,
                             start + len(data) // 2, perf_counter(), "silence")

    failure = None
    try:
        worker.start()
        jobs = [(segment(pcm[0] + pcm[1] + pcm[0]), "System"),
                (segment(pcm[1], 160000), "System"),
                (segment(pcm[0][:8000], 320000), "System"),
                (replace(segment(struct.pack("<h", 100) * 32000), reason="silence"), "Me")]
        for job, source in jobs:
            before = worker.stats["completed"]
            if not worker.submit(job, speaker=source):
                raise RuntimeError("Smoke job rejected")
            deadline = perf_counter() + 60
            while worker.stats["completed"] == before:
                worker.poll()
                if perf_counter() > deadline:
                    raise RuntimeError("Smoke timeout")
                sleep(0.01)
        worker.close()
    except Exception as error:
        failure = str(error)
    finally:
        worker.close(drain=False)
    report = {"scope": "Public English A/B/A clips through Armenian ASR; routing, not ASR accuracy",
              "source_speaker_ids": speakers, "events": events, "inference": worker.summary(),
              "error": failure, "wall_s": perf_counter() - started}
    Path("reports/stage42_pipeline.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"labels": [event["speaker"] for event in events],
                      "inference": worker.summary(), "error": failure}, indent=2))
    if failure:
        raise RuntimeError(failure)


if __name__ == "__main__":
    main()

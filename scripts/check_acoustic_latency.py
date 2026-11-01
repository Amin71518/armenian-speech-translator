"""Opt-in speaker -> real microphone -> VAD/ASR/MT test; audio stays in RAM only.

The user must authorize audible playback first. ADC clock and waveform-only
annotations are unvalidated, so results are estimates, not a physical certificate.
"""

import argparse
import hashlib
import json
import sys
import threading
import wave
from dataclasses import asdict
from pathlib import Path
from queue import Empty, Full, Queue
from time import perf_counter

import av
import numpy as np
import psutil
import sounddevice as sd

from armenian_speech.cli import read_manifest
from armenian_speech.latency import (
    align_reference,
    clock_sample,
    evaluate_cases,
    numeric_result,
)
from armenian_speech.live_pipeline import InferenceWorker, WorkerConfig
from armenian_speech.live_vad import LiveVAD, PCMResampler
from armenian_speech.microphone import MicrophoneCapture
from armenian_speech.vad import SileroVAD


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--input-device", type=int, default=9)
    cli.add_argument("--output-device", type=int, default=8)
    cli.add_argument("--samples", nargs="+", help="Reference WAV names; default: six examples")
    cli.add_argument("--peak", type=float,
                     help="Normalize fixture peaks to (0, 0.5]; Windows volume unchanged")
    cli.add_argument("--report", type=Path, required=True)
    args = cli.parse_args()
    if args.peak is not None and not 0 < args.peak <= 0.5:
        raise ValueError("Fixture peak must be in (0, 0.5].")
    names = set(args.samples or (
        "001.wav", "003.wav", "004.wav", "006.wav", "009.wav", "015.wav",
    ))
    rows = [r for r in read_manifest(Path("data/local/fleurs/manifest.jsonl"))
            if r["path"].name in names]
    if {row["path"].name for row in rows} != names:
        raise ValueError("Unknown fixture name.")
    annotation = json.loads(Path("data/latency_endpoints.json").read_text(encoding="utf-8"))
    labels = {r["sample"]: r for r in annotation["recordings"]}
    pieces, fixtures, cursor = [b"\0\0" * 16000], [], 16000
    for row in rows:
        if hashlib.sha256(row["path"].read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Reference checksum mismatch.")
        if labels[row["path"].name]["sha256"] != row["sha256"]:
            raise ValueError("Annotation checksum mismatch.")
        with wave.open(str(row["path"]), "rb") as audio:
            data = audio.readframes(audio.getnframes())
        samples = np.frombuffer(data, dtype="<i2").astype(np.float64)
        peak = float(np.max(np.abs(samples))) / 32768
        gain = args.peak / peak if args.peak is not None and peak else 1.0
        fixtures.append({"id": row["path"].name, "offset_s": cursor / 16000,
                         "pcm": data, "label": labels[row["path"].name], "playback_gain": gain})
        pieces.extend((np.rint(samples * gain).astype("<i2").tobytes(), b"\0\0" * 48000))
        cursor += len(data) // 2 + 48000
    source = b"".join(pieces)
    frame = av.AudioFrame.from_ndarray(np.frombuffer(source, dtype="<i2").reshape(1, -1),
                                      format="s16", layout="mono")
    frame.sample_rate = 16000
    resampler = av.AudioResampler(format="s16", layout="mono", rate=48000)
    frames = resampler.resample(frame) + resampler.resample(None)
    mono = np.concatenate([f.to_ndarray().reshape(-1) for f in frames])
    playback = np.repeat(mono[:, None], 2, axis=1).astype("<i2").tobytes()
    output_position = 0
    output_status = {"events": 0, "timing_queue_drops": 0}
    timings: Queue = Queue(maxsize=64)
    finished = threading.Event()

    def play(outdata, count, timing, status):
        nonlocal output_position
        start = output_position
        data = playback[start * 4:(start + count) * 4]
        outdata[:] = data + b"\0" * (len(outdata) - len(data))
        output_position += count
        output_status["events"] += bool(status)
        try:
            timings.put_nowait((start, float(timing.outputBufferDacTime)))
        except Full:
            output_status["timing_queue_drops"] += 1
        if output_position * 4 >= len(playback):
            raise sd.CallbackStop

    capture = MicrophoneCapture()
    vad = LiveVAD(SileroVAD(Path(".cache/models/silero")), 48000, 1)
    results, offers, anchors, recorded = [], [], [], bytearray()
    worker = InferenceWorker(WorkerConfig(Path(".cache/models")),
                             on_result=lambda event: results.append(numeric_result(event)))
    input_stream = output_stream = None
    first_dac = None
    clock_in = clock_out = None
    failure = None
    power_start = psutil.sensors_battery()
    max_frames = int(len(mono) / 48000 + 10) * 48000

    def submit(segments):
        for segment in segments:
            accepted = worker.submit(segment)
            offers.append({"sequence": worker.stats["offered"], "accepted": accepted,
                           "source": segment.metadata()})

    def consume(block):
        if block.start_frame + block.frames > max_frames:
            raise RuntimeError("Acoustic capture exceeded the bounded test buffer.")
        missing = block.start_frame - len(recorded) // 2
        if missing < 0:
            raise RuntimeError("Captured frames overlapped.")
        recorded.extend(b"\0\0" * missing)
        recorded.extend(block.pcm)
        anchors.append(block)
        submit(vad.push(block))

    try:
        worker.start()
        input_stream = sd.RawInputStream(device=args.input_device, samplerate=48000, channels=1,
                                         dtype="int16", blocksize=0, callback=capture.callback)
        output_stream = sd.RawOutputStream(
            device=args.output_device, samplerate=48000, channels=2, dtype="int16",
            blocksize=0, callback=play, finished_callback=finished.set,
        )
        input_stream.start()
        clock_in = clock_sample(lambda: input_stream.time)
        output_stream.start()
        clock_out = clock_sample(lambda: output_stream.time)
        deadline = perf_counter() + len(mono) / 48000 + 3
        while perf_counter() < deadline:
            worker.poll()
            try:
                consume(capture.blocks.get(timeout=0.02))
            except Empty:
                pass
            if capture.error is not None:
                raise RuntimeError(f"Capture callback error: {capture.error}")
            while not timings.empty():
                position, dac = timings.get_nowait()
                if position == 0:
                    first_dac = dac
        if not finished.is_set():
            raise RuntimeError("Playback did not finish within the capture window.")
        output_stream.close()
        input_stream.close()
        while not capture.blocks.empty():
            consume(capture.blocks.get_nowait())
        submit(vad.finish(final_input_frame=capture.stats.frames,
                          final_capture_epoch=capture.capture_epoch))
        worker.close()
    except (Exception, KeyboardInterrupt) as error:
        failure = f"{type(error).__name__}: {error}"
    finally:
        if output_stream is not None:
            output_stream.abort()
            output_stream.close()
        if input_stream is not None:
            input_stream.close()
        try:
            worker.close(drain=False)
        except Exception as error:
            failure = failure or str(error)
    references, alignments = [], []
    if anchors and first_dac is not None and clock_in and clock_out:
        converter = PCMResampler(48000, 1)
        mic = np.frombuffer(converter.push(bytes(recorded)) + converter.finish(), dtype="<i2")
        input_start = anchors[0].adc_time + clock_in["offset_s"]
        playback_start = first_dac + clock_out["offset_s"]
        for fixture in fixtures:
            expected = round((playback_start + fixture["offset_s"] - input_start) * 16000)
            try:
                aligned = align_reference(mic, np.frombuffer(fixture["pcm"], dtype="<i2"),
                                          expected, 16000)
            except ValueError as error:
                alignments.append({"id": fixture["id"], "reliable": False, "error": str(error)})
                references.append({"id": fixture["id"], "unavailable_reason": "alignment_failed"})
                continue
            alignments.append({"id": fixture["id"], **aligned})
            if not aligned["reliable"]:
                references.append({"id": fixture["id"], "unavailable_reason": "alignment_failed"})
                continue
            interval = [aligned["start_sample"] / 16000 + end
                        for end in fixture["label"]["speech_end_interval_s"]]
            mapped, delivery_proxy = [], []
            for end in interval:
                position = end * 48000
                anchor = next(a for a in reversed(anchors) if a.start_frame <= position)
                relative = (position - anchor.start_frame) / 48000
                mapped.append(anchor.adc_time + clock_in["offset_s"] + relative)
                delivery_proxy.append(anchor.received_monotonic - anchor.frames / 48000 + relative)
            references.append({"id": fixture["id"], "end_interval_s": interval,
                               "end_monotonic_interval": mapped,
                               "callback_delivery_proxy_interval": delivery_proxy})
    known = {reference["id"] for reference in references}
    references.extend({"id": fixture["id"], "unavailable_reason": "capture_or_playback_unavailable"}
                      for fixture in fixtures if fixture["id"] not in known)
    matched = sum("end_interval_s" in reference for reference in references)
    evaluation = evaluate_cases(references, offers, results)
    captured_samples = np.frombuffer(recorded, dtype="<i2").astype(np.float64)
    report = {
        "scope": "Actual speaker -> microphone -> models; provisional waveform/ADC time estimates",
        "physical_latency_certified": False, "annotation_review_skipped_by_user": True,
        "clock_warning": "ADC timestamps were future-dated in the separate probe; no correction",
        "expected_recordings": len(fixtures), "alignment_failures": len(fixtures) - matched,
        "playback_gains": {fixture["id"]: fixture["playback_gain"] for fixture in fixtures},
        "captured_peak": float(np.max(np.abs(captured_samples))) / 32768
        if len(captured_samples) else None,
        "captured_rms": float(np.sqrt(np.mean(captured_samples**2))) / 32768
        if len(captured_samples) else None,
        "alignments": alignments, "references": references, "evaluation": evaluation,
        "capture": asdict(capture.stats), "vad": vad.stats, "output": output_status,
        "input_stream_closed": input_stream.closed if input_stream else None,
        "output_stream_closed": output_stream.closed if output_stream else None,
        "input_clock": clock_in, "output_clock": clock_out,
        "offers": offers, "results": results, "inference": worker.summary(),
        "power_start": power_start._asdict() if power_start else None,
        "power_end": psutil.sensors_battery()._asdict(), "error": failure,
    }
    recorded.clear()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "alignment": alignments, "evaluation": evaluation, "error": failure,
    }, indent=2))
    if failure:
        raise RuntimeError(failure)


if __name__ == "__main__":
    main()

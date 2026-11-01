"""Bounded live inference in one spawned process; terminal output stays in the parent."""

import json
import math
import multiprocessing as mp
import os
import signal
import sys
import unicodedata
import wave
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from queue import Empty, Full
from time import perf_counter
from uuid import uuid4

from armenian_speech.output import print_segment


@dataclass(frozen=True)
class WorkerConfig:
    cache_dir: Path
    asr_model: Path | None = None
    threads: int = 4
    filter_asr_fragments: bool = True
    diarize_system: bool = False
    speaker_threshold: float = 0.47
    speaker_margin: float = 0.08
    max_speakers: int = 8
    speaker_diagnostics: bool = False
    experimental_speaker_matching: bool = False


@dataclass(frozen=True)
class InferenceJob:
    sequence: int
    segment: object
    enqueued_monotonic: float
    speaker: str | None = None


def load_models(config: WorkerConfig):
    from armenian_speech.asr_onnx import OnnxArmenianASR
    from armenian_speech.translation import ArmenianTranslator

    directory = config.asr_model or config.cache_dir / "vana"
    if not (directory / "PROVENANCE.json").is_file():
        raise FileNotFoundError(
            "Prepared ASR missing. Run: poetry run python scripts/download_asr.py"
        )
    before = perf_counter()
    asr = OnnxArmenianASR(directory, config.threads)
    asr_load = perf_counter() - before
    before = perf_counter()
    translator = ArmenianTranslator(config.cache_dir, config.threads, True)
    return asr, translator, {
        "asr_load_s": asr_load, "translation_load_s": perf_counter() - before,
        "asr_model": asr.provenance["repo"], "asr_revision": asr.provenance["revision"],
        "translation_revision": translator.revision,
    }


def asr_fragment_reason(text: str) -> str | None:
    """Reject isolated letter fragments, not short words or numbers.

    This is a structural live-output guard, not a confidence/meaning detector.
    Preserve Armenian single-letter words; casefold also expands Armenian ligatures.
    """
    normalized = unicodedata.normalize("NFC", text).casefold()
    if any(character.isnumeric() for character in normalized):
        return None
    letters = "".join(character for character in normalized if character.isalpha())
    if not letters:
        return "no_alphanumeric"
    if len(letters) == 1 and letters not in {"ա", "է"}:
        return "single_letter"
    return None


def process_segment(
    job: InferenceJob, asr, translator, wav_path: Path, dequeued: float,
    *, filter_asr_fragments: bool = True,
) -> dict:
    """Close the temporary WAV before ASR reads it; clean it up on every exception."""
    segment = job.segment
    try:
        with wave.open(str(wav_path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(segment.pcm)
        before = perf_counter()
        recognized, duration = asr.transcribe(wav_path)
        asr_finished = perf_counter()
        asr_s = asr_finished - before
        asr_started = before
    finally:
        wav_path.unlink(missing_ok=True)
    armenian = " ".join(item.text for item in recognized).strip()
    before = perf_counter()
    skip_reason = asr_fragment_reason(armenian) if armenian and filter_asr_fragments else None
    if skip_reason is not None:
        armenian = ""
    parts = translator.split_text(armenian) if armenian else []
    english = " ".join(translator.translate(part) for part in parts)
    finished = perf_counter()
    return {
        "kind": "result", "sequence": job.sequence,
        "speaker": job.speaker,
        "armenian": armenian, "english": english, "translation_parts": len(parts),
        "skip_reason": skip_reason,
        "start_s": segment.origin_s + segment.start_sample / 16000,
        "duration_s": duration, "source": segment.metadata(),
        "enqueued_monotonic": job.enqueued_monotonic, "dequeued_monotonic": dequeued,
        "asr_started_monotonic": asr_started, "asr_finished_monotonic": asr_finished,
        "translation_started_monotonic": before, "worker_finished_monotonic": finished,
        "queue_wait_s": dequeued - job.enqueued_monotonic,
        "asr_s": asr_s, "translation_s": finished - before, "worker_s": finished - dequeued,
    }


def _worker_main(config, jobs, events, control, wav_path, model_factory, speaker_factory=None):
    # Ctrl+C belongs to the parent: it closes capture, then drains or terminates us.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[name] = str(config.threads)
    sequence = None
    try:
        asr, translator, metadata = (model_factory or load_models)(config)
        tracker = None
        if config.diarize_system:
            from armenian_speech.speakers import Extractor, SpeakerTracker

            tracker = (speaker_factory(config) if speaker_factory else SpeakerTracker(
                Extractor(directory=config.cache_dir / "speakers" / "campplus"),
                config.speaker_threshold, config.speaker_margin, config.max_speakers,
                experimental=config.experimental_speaker_matching,
            ))
            metadata["diarization"] = "campplus_cpu_1t_experimental"
            metadata["speaker_matching_policy"] = (
                "short_views_and_anchored_halves_trial" if config.experimental_speaker_matching
                else "first42")
        events.send({"kind": "ready", **metadata})
        processed = 0
        expected = None
        while expected is None or processed < expected:
            if control.poll():
                expected = control.recv()
            if expected is not None and processed >= expected:
                break
            try:
                job = jobs.get(timeout=0.1)
            except Empty:
                continue
            dequeued = perf_counter()
            sequence = job.sequence
            events.send({"kind": "started", "sequence": sequence})
            if tracker and job.speaker == "System":
                if config.speaker_diagnostics:
                    def decision(details, current_job=job):
                        events.send({"kind": "speaker_decision", "sequence": current_job.sequence,
                                     "source_label": current_job.speaker,
                                     "source": current_job.segment.metadata(), **details})

                    parts = tracker.split(job.segment, on_decision=decision)
                else:
                    parts = tracker.split(job.segment)
            else:
                parts = [(job.segment, job.speaker)]
            for index, (segment, label) in enumerate(parts):
                event = process_segment(
                    replace(job, segment=segment, speaker=label),
                    asr, translator, wav_path, dequeued,
                    filter_asr_fragments=config.filter_asr_fragments,
                )
                events.send({**event, "source_label": job.speaker,
                             "part_index": index, "last_part": index == len(parts) - 1,
                             "diarization": ({**tracker.stats,
                                 "speakers": len(tracker.registry.centroids)}
                                 if tracker else None)})
            processed += 1
        events.send({"kind": "stopped", "processed": processed})
    except BaseException as error:
        try:
            events.send({"kind": "error", "sequence": sequence,
                         "message": f"{type(error).__name__}: {error}"})
        except (OSError, EOFError):
            pass
        raise SystemExit(1) from error
    finally:
        events.close()
        control.close()
        jobs.close()


class InferenceWorker:
    """One producer, capacity-limited jobs, and a bounded OS pipe for results.

    Full queue drops the incoming phrase. No inference or model-loading waits occur
    in submit(). close() drains to an explicit deadline, then kills a stuck process.
    """

    def __init__(
        self, config: WorkerConfig, *, capacity: int = 2, shutdown_timeout: float = 15.0,
        model_factory=None, diagnostics: bool = False,
        on_result: Callable[[dict], None] | None = None,
        speaker: str = "Me",
        speaker_factory=None,
        on_speaker_decision: Callable[[dict], None] | None = None,
    ) -> None:
        if capacity < 1 or not math.isfinite(shutdown_timeout) or shutdown_timeout <= 0:
            raise ValueError("Queue capacity and shutdown timeout must be positive.")
        self.config = config
        self.speaker = speaker
        self.capacity = capacity
        self.shutdown_timeout = shutdown_timeout
        self.model_factory = model_factory
        self.speaker_factory = speaker_factory
        self.diagnostics = diagnostics
        self.on_result = on_result
        self.on_speaker_decision = on_speaker_decision
        self.context = mp.get_context("spawn")
        self.jobs = self.context.Queue(maxsize=capacity)
        self.events, self._sender = self.context.Pipe(duplex=False)
        self._control, self._finish_sender = self.context.Pipe(duplex=False)
        self.finishing = False
        self.process = None
        self.session_dir: Path | None = None
        self.closed = False
        self.ready = False
        self._eof = False
        self.error: str | None = None
        self.metadata: dict = {}
        self.source_stats = {}
        self.stats = {
            "offered": 0, "accepted": 0, "dropped_full": 0, "skipped_gap": 0,
            "started": 0, "completed": 0, "empty_asr": 0, "translation_parts": 0,
            "filtered_asr_fragments": 0,
            "peak_queue_depth": 0, "max_queue_wait_s": 0.0, "sum_queue_wait_s": 0.0,
            "sum_asr_s": 0.0, "sum_translation_s": 0.0,
            "max_decision_to_output_s": 0.0, "forced_termination": False,
            "discarded_on_shutdown": 0, "worker_exitcode": None,
            "result_parts": 0,
        }

    def start(self, timeout: float = 120.0) -> None:
        if self.process is not None or self.closed:
            raise RuntimeError("Inference worker cannot be started twice.")
        base = (Path.cwd() / ".cache" / "live").resolve()
        base.mkdir(parents=True, exist_ok=True)
        self.session_dir = base / ("session-" + uuid4().hex)
        self.session_dir.mkdir()
        self.process = self.context.Process(
            target=_worker_main,
            args=(self.config, self.jobs, self._sender, self._control,
                  self.session_dir / "segment.wav", self.model_factory, self.speaker_factory),
            name="armenian-inference",
        )
        try:
            self.process.start()
            self._sender.close()
            self._control.close()
            deadline = perf_counter() + timeout
            while not self.ready:
                self.poll()
                if perf_counter() >= deadline:
                    raise RuntimeError("Inference model startup exceeded its timeout.")
                self.process.join(0.05)
        except BaseException:
            self.close(drain=False)
            raise

    def submit(self, segment, *, speaker=None) -> bool:
        if self.closed or not self.ready or self.finishing:
            raise RuntimeError("Inference worker is not accepting phrases.")
        self.poll()
        speaker = self.speaker if speaker is None else speaker
        counts = self.source_stats.setdefault(speaker, {
            "offered": 0, "accepted": 0, "completed": 0, "dropped_full": 0,
            "skipped_gap": 0, "empty_asr": 0, "filtered_asr_fragments": 0,
        })
        counts["offered"] += 1
        self.stats["offered"] += 1
        sequence = self.stats["offered"]
        if segment.reason == "gap":
            counts["skipped_gap"] += 1
            self.stats["skipped_gap"] += 1
            print(f"Inference: skipped incomplete gap phrase {sequence}.",
                  file=sys.stderr, flush=True)
            return False
        samples = len(segment.pcm) // 2
        if len(segment.pcm) % 2 or not 0 < samples <= 192000:
            raise ValueError("Inference requires 1–192000 mono PCM16 16 kHz samples.")
        if segment.end_sample - segment.start_sample != samples:
            raise ValueError("Phrase PCM length disagrees with its sample bounds.")
        try:
            self.jobs.put_nowait(InferenceJob(sequence, segment, perf_counter(), speaker))
        except Full:
            counts["dropped_full"] += 1
            self.stats["dropped_full"] += 1
            print(f"Inference queue full: dropped incoming phrase {sequence}.",
                  file=sys.stderr, flush=True)
            return False
        self.stats["accepted"] += 1
        counts["accepted"] += 1
        self.stats["peak_queue_depth"] = max(self.stats["peak_queue_depth"], self.jobs.qsize())
        return True

    def _event(self, event: dict) -> None:
        kind = event["kind"]
        if kind == "ready":
            self.ready = True
            self.metadata = {key: value for key, value in event.items() if key != "kind"}
        elif kind == "error":
            self.error = (
                f"Inference worker failed on phrase {event['sequence']}: {event['message']}"
            )
        elif kind == "started":
            self.stats["started"] += 1
        elif kind == "speaker_decision":
            if self.config.speaker_diagnostics:
                keys = ("sequence", "start_s", "duration_s", "label", "reason", "best",
                        "second", "half_score", "half_matches", "embedding_rejection",
                        "counts_before", "counts_after")
                keys += ("probe_kind", "experimental")
                compact = {key: event[key] for key in keys}
                print("Speaker decision: " + json.dumps(compact, allow_nan=False), flush=True)
                if self.on_speaker_decision is not None:
                    self.on_speaker_decision(event)
        elif kind == "result":
            label = event.get("speaker") or self.speaker
            counts = self.source_stats[event.get("source_label") or label]
            self.stats["result_parts"] += 1
            if event.get("diarization") is not None:
                self.metadata["diarization_stats"] = event["diarization"]
            if event["skip_reason"] is not None:
                counts["filtered_asr_fragments"] += 1
                self.stats["filtered_asr_fragments"] += 1
                if self.diagnostics:
                    print(
                        f"Inference phrase {event['sequence']}: skipped ASR fragment "
                        f"({event['skip_reason']}).", flush=True,
                    )
            elif event["armenian"]:
                print_segment(event["start_s"], label, event["armenian"], event["english"])
            else:
                counts["empty_asr"] += 1
                self.stats["empty_asr"] += 1
                if self.diagnostics:
                    print(f"Inference phrase {event['sequence']}: empty ASR.", flush=True)
            output_finished = perf_counter()
            if event.get("last_part", True):
                self.stats["completed"] += 1
                counts["completed"] += 1
            self.stats["translation_parts"] += event["translation_parts"]
            if event.get("part_index", 0) == 0:
                self.stats["sum_queue_wait_s"] += event["queue_wait_s"]
            self.stats["max_queue_wait_s"] = max(
                self.stats["max_queue_wait_s"], event["queue_wait_s"],
            )
            self.stats["sum_asr_s"] += event["asr_s"]
            self.stats["sum_translation_s"] += event["translation_s"]
            decision_delay = output_finished - event["source"]["decision_monotonic"]
            printed = event["skip_reason"] is None and bool(event["armenian"])
            if printed:
                self.stats["max_decision_to_output_s"] = max(
                    self.stats["max_decision_to_output_s"], decision_delay,
                )
            if self.on_result is not None:
                self.on_result({
                    **event, "printed": printed,
                    "output_finished_monotonic": output_finished if printed else None,
                    "completion_monotonic": output_finished,
                })
            if self.diagnostics:
                endpoint = "output" if printed else "completion"
                print(
                    f"Inference {event['sequence']}: queue={event['queue_wait_s']:.3f}s "
                    f"ASR={event['asr_s']:.3f}s MT={event['translation_s']:.3f}s "
                    f"parts={event['translation_parts']} "
                    f"VAD-decision→{endpoint}={decision_delay:.3f}s "
                    "(not speech-end latency)", flush=True,
                )

    def poll(self) -> None:
        if self.closed:
            return
        while not self._eof:
            try:
                if not self.events.poll():
                    break
                event = self.events.recv()
            except (EOFError, BrokenPipeError):
                self._eof = True
            else:
                self._event(event)
        if self.error:
            raise RuntimeError(self.error)
        if self.process is not None and self.process.exitcode is not None:
            if self.process.exitcode != 0 or not self.finishing:
                raise RuntimeError(f"Inference worker exited unexpectedly: {self.process.exitcode}")

    def close(self, *, drain: bool = True) -> None:
        if self.closed:
            return
        failure = None
        try:
            if self.process is not None and self.process.pid is not None:
                if drain:
                    self.poll()
                    # One small control message avoids a sentinel blocked behind a full job queue.
                    # The count also covers jobs still in Queue's asynchronous feeder.
                    self.finishing = True
                    try:
                        self._finish_sender.send(self.stats["accepted"])
                    except BrokenPipeError:
                        self.process.join(0.05)
                        # Preserve any model error/exit code already sent by the worker.
                        self.poll()
                        raise RuntimeError(
                            "Inference control channel closed before shutdown."
                        ) from None
                    deadline = perf_counter() + self.shutdown_timeout
                    while self.process.is_alive():
                        self.poll()
                        remaining = deadline - perf_counter()
                        if remaining <= 0:
                            failure = RuntimeError(
                                "Inference shutdown timed out; unfinished phrases discarded."
                            )
                            break
                        self.process.join(min(0.05, remaining))
                    if failure is None:
                        self.poll()
                        if self.stats["completed"] != self.stats["accepted"]:
                            failure = RuntimeError(
                                "Worker exited before all accepted phrases completed."
                            )
        except BaseException as error:
            failure = error
        finally:
            if self.process is not None and self.process.pid is not None:
                if self.process.is_alive():
                    self.stats["forced_termination"] = True
                    self.process.terminate()
                    self.process.join(2)
                    if self.process.is_alive():
                        self.process.kill()
                        self.process.join(2)
                self.stats["worker_exitcode"] = self.process.exitcode
                if self.process.is_alive():
                    failure = RuntimeError("Inference process did not exit after termination.")
                else:
                    self.process.close()
            self.stats["discarded_on_shutdown"] = self.stats["accepted"] - self.stats["completed"]
            # Do not join a feeder that may be writing to a terminated consumer.
            self.jobs.cancel_join_thread()
            self.jobs.close()
            self.events.close()
            self._sender.close()
            self._control.close()
            self._finish_sender.close()
            self.closed = True
            if self.session_dir is not None:
                # Only our exact WAV and then an empty directory; no recursive deletion.
                (self.session_dir / "segment.wav").unlink(missing_ok=True)
                self.session_dir.rmdir()
        if failure is not None:
            raise failure

    def summary(self) -> dict:
        return {**self.stats, "capacity": self.capacity, "overflow_policy": "drop_incoming",
                "sources": {key: {**value, "unfinished": value["accepted"] - value["completed"]}
                            for key, value in self.source_stats.items()},
                "asr_fragment_filter": self.config.filter_asr_fragments,
                "models": self.metadata, "worker_closed": self.closed}

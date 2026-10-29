"""Local Vana-Labs INT8 RNN-T adapter; file bounds are not detected speech bounds."""

import json
import wave
from pathlib import Path

from armenian_speech.asr import Segment


class OnnxArmenianASR:
    def __init__(self, directory: Path, threads: int) -> None:
        import onnx_asr
        import onnxruntime as ort

        self.provenance = json.loads((directory / "PROVENANCE.json").read_text(encoding="utf-8"))
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.model = onnx_asr.load_model(
            "nemo-conformer-rnnt", str(directory), quantization="int8",
            providers=["CPUExecutionProvider"], sess_options=options,
        )

    def transcribe(self, path: Path) -> tuple[list[Segment], float]:
        with wave.open(str(path), "rb") as wav:
            if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (16000, 1, 2):
                raise ValueError("ONNX experiment requires mono PCM16 16 kHz WAV")
            duration = wav.getnframes() / wav.getframerate()
        text = self.model.recognize(str(path)).strip()
        return ([Segment(0.0, duration, text)] if text else []), duration

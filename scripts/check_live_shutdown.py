"""Windows hidden-console CTRL_C_EVENT test; persist numeric results only."""

import argparse
import ctypes
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from time import perf_counter, sleep

import psutil


def send_ctrl_c(pid: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.FreeConsole()
    if not kernel.AttachConsole(pid):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not kernel.SetConsoleCtrlHandler(None, True):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel.GenerateConsoleCtrlEvent(0, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        sleep(0.1)
    finally:
        kernel.FreeConsole()


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--device", type=int, default=9)
    cli.add_argument("--source", choices=("microphone", "system_audio", "combined"),
                     default="microphone")
    cli.add_argument("--microphone-device", type=int, default=9)
    cli.add_argument("--live", action="store_true", help="Enable models for system_audio")
    cli.add_argument("--diarize", action="store_true")
    cli.add_argument("--seconds", type=float, default=5)
    cli.add_argument("--report", type=Path, required=True)
    args = cli.parse_args()
    if os.name != "nt":
        raise RuntimeError("This test requires the Windows console API.")
    if not 0 < args.seconds <= 300:
        raise ValueError("Test capture duration must be in (0, 300] seconds.")
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    command = [sys.executable, "-m", f"armenian_speech.{args.source}",
               "--device", str(args.device)]
    if args.source == "microphone":
        command.extend(["--sample-rate", "48000", "--live", "--diagnostics"])
    elif args.source == "combined":
        command.extend(["--microphone-device", str(args.microphone_device), "--diagnostics"])
    elif args.live:
        command.extend(["--live", "--diagnostics"])
    if args.diarize:
        if args.source == "microphone":
            cli.error("Diarization is System-only")
        command.append("--diarize")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        startupinfo=startup, creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    active = threading.Event()
    observation = {"terminal_pairs": 0, "summary": None, "error_lines": 0}

    def read_output():
        for line in process.stdout:
            if ("Microphone active." in line or "Monitoring only;" in line
                    or "System Audio live active." in line or "Combined live active." in line):
                active.set()
            if "  HY:" in line:
                observation["terminal_pairs"] += 1
            if line.startswith("Capture summary: "):
                observation["summary"] = json.loads(line.removeprefix("Capture summary: "))
            if line.startswith("Error:"):
                observation["error_lines"] += 1

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    identities = []
    failure = None
    shutdown_s = None
    cleanup_kills = 0
    try:
        deadline = perf_counter() + 120
        while not active.is_set():
            if process.poll() is not None:
                raise RuntimeError("App exited before microphone activation.")
            if perf_counter() >= deadline:
                raise RuntimeError("Microphone activation timed out.")
            sleep(0.05)
        root = psutil.Process(process.pid)
        identities = [root, *root.children(recursive=True)]
        sleep(args.seconds)
        before = perf_counter()
        send_ctrl_c(process.pid)
        process.wait(timeout=25)
        shutdown_s = perf_counter() - before
        reader.join(timeout=3)
        _, alive = psutil.wait_procs(identities, timeout=3)
        if alive:
            raise RuntimeError("App/worker process remained after Ctrl+C.")
        summary = observation["summary"]
        if process.returncode != 130 or summary is None:
            raise RuntimeError("Expected Ctrl+C exit 130 and a numeric capture summary.")
        if not summary["stream_closed"] or (
            "inference" in summary and not summary["inference"]["worker_closed"]
        ):
            raise RuntimeError("Stream or worker did not close.")
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
    finally:
        if process.poll() is None and not identities:
            root = psutil.Process(process.pid)
            identities = [root, *root.children(recursive=True)]
        for identity in reversed(identities):
            try:
                if identity.is_running():
                    identity.kill()
                    cleanup_kills += 1
            except psutil.NoSuchProcess:
                pass
        psutil.wait_procs(identities, timeout=3)
        process.wait(timeout=5)
        reader.join(timeout=3)
    report = {
        "scope": "Actual CTRL_C_EVENT to a private hidden Windows console",
        "capture_requested_s": args.seconds, "exit_code": process.returncode,
        "source": args.source,
        "shutdown_s": shutdown_s, "controller_cleanup_kills": cleanup_kills,
        "error": failure, **observation,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failure:
        raise RuntimeError(failure)


if __name__ == "__main__":
    main()

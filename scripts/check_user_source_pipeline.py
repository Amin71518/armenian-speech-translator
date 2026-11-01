"""Real spawned ASR/MT replay of authorized excerpts; no capture or saved hypotheses."""

import json
from pathlib import Path
from time import perf_counter, sleep

from armenian_speech.latency import numeric_result
from armenian_speech.live_pipeline import InferenceWorker, WorkerConfig
from scripts.check_user_sources import prepared_sources


def main():
    import sys

    sys.stdout.reconfigure(encoding='utf-8')
    _, clips, details = prepared_sources()
    report = {'scope': 'Paced direct-file replay, not live channel, DER, WER or E2E latency',
              'sources': details, 'runs': []}
    target = Path('reports/user_source_pipeline_trial.json')
    if target.exists():
        raise FileExistsError(target)
    for experimental in (False, True):
        events = []
        worker = InferenceWorker(
            WorkerConfig(Path('.cache/models'), diarize_system=True,
                         experimental_speaker_matching=experimental),
            on_result=lambda e, out=events: out.append(numeric_result(e)),
        )
        failure = None
        try:
            worker.start()
            for owner in list(clips) * 3:
                for phrase in clips[owner]:
                    before = worker.stats['completed']
                    if not worker.submit(phrase, speaker='System'):
                        raise RuntimeError('Paced job was rejected')
                    deadline = perf_counter() + 60
                    while worker.stats['completed'] == before:
                        worker.poll()
                        if perf_counter() > deadline:
                            raise TimeoutError('Paced replay timeout')
                        sleep(0.01)
            worker.close()
        except Exception as error:
            failure = str(error)
        finally:
            worker.close(drain=False)
        report['runs'].append({'experimental': experimental, 'error': failure,
                               'inference': worker.summary(), 'events': events,
                               'session_cleaned': not worker.session_dir.exists()})
        target.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({'experimental': experimental, 'error': failure,
                          'inference': worker.summary()}), flush=True)
        if failure:
            raise RuntimeError(failure)


if __name__ == '__main__':
    main()

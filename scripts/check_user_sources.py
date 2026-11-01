"""Reproduce user-authorized public excerpts through actual VAD and offline speaker policies."""

import hashlib
import json
from pathlib import Path

import av
import numpy as np

from armenian_speech.speakers import SpeakerTracker
from armenian_speech.vad import SileroVAD
from scripts.check_speaker_candidates import evaluate
from scripts.check_speaker_decisions import CachedExtractor
from scripts.check_vad import replay


def decode(path):
    pieces = []
    resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
    with av.open(str(path)) as container:
        for frame in container.decode(audio=0):
            pieces.extend(f.to_ndarray().tobytes() for f in resampler.resample(frame))
        pieces.extend(f.to_ndarray().tobytes() for f in resampler.resample(None))
    return np.frombuffer(b''.join(pieces), dtype='<i2').astype(np.float32) / 32768


def prepared_sources():
    directory = Path('data/local/user_source_sections')
    provenance = json.loads((directory / 'PROVENANCE.json').read_text(encoding='utf-8'))
    model = SileroVAD(Path('.cache/models/silero'))
    clips, details = {}, {}
    for row in provenance:
        if 'error' in row:
            raise RuntimeError(row['error'])
        path = Path(row['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Source section checksum mismatch')
        pcm = decode(path)
        if abs(len(pcm) / 16000 - (row['end_s'] - row['start_s'])) > 0.1:
            raise ValueError('Downloaded section duration mismatch')
        # Insert known surrounding silence, never count it as labelled speech.
        padded = np.concatenate((np.zeros(16000, dtype=np.float32), pcm,
                                 np.zeros(16000, dtype=np.float32)))
        parts, stats = replay(model, (padded * 32768).astype('<i2').tobytes())
        clips[row['video']] = parts
        details[row['video']] = {'decoded_duration_s': len(pcm) / 16000,
                                 'vad_segments': [p.metadata() for p in parts], 'vad': stats}
    return provenance, clips, details


def main():
    provenance, clips, details = prepared_sources()
    order = list(clips) * 3
    jobs = [(owner, np.frombuffer(part.pcm, dtype='<i2').astype(np.float32) / 32768)
            for owner in order for part in clips[owner]]
    extractor = CachedExtractor()
    policies = {'baseline': {}, 'anchored': {'anchored': True},
                'short_1.5': {'short': True, 'short_min': 24000},
                'short_1.25': {'short': True},
                'both_1.5': {'short': True, 'short_min': 24000, 'anchored': True}}
    results = {name: evaluate(jobs, extractor, **flags) for name, flags in policies.items()}
    all_traces = {}
    for experimental, policy in [(False, 'baseline'), (True, 'both_1.5')]:
        tracker, traces = SpeakerTracker(extractor, experimental=experimental), []
        for owner in order:
            for part in clips[owner]:
                tracker.split(part, on_decision=lambda d, s=owner, out=traces:
                              out.append({'owner': s, **d}))
        if [(d['label'], d['duration_s']) for d in traces] != [
                (d['label'], d['seconds']) for d in results[policy]['decisions']]:
            raise AssertionError('Candidate and production tracker differ')
        all_traces[policy] = traces
    report = {'scope': 'Exact user-specified public sources, repeated A/B; not live-channel DER',
              'provenance': provenance, 'source_details': details, 'order': order,
              'results': results, 'production_traces': all_traces,
              'limitations': ['Source ownership from user; no word/speech/overlap annotation',
                              'Direct files, not actual Bluetooth or WASAPI signal',
                              'Same clips repeated three times; not independent observations']}
    target = Path('reports/user_sources_production_verified.json')
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    for name, result in results.items():
        print(name, json.dumps({k: v for k, v in result.items() if k != 'decisions'}))
    for source, info in details.items():
        print(source, 'VAD lengths:', [p['samples'] / 16000 for p in info['vad_segments']])


if __name__ == '__main__':
    main()

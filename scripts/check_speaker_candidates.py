"""Offline ablation of anchored halves and single-utterance short enrollment; no capture."""

import json
from collections import Counter
from pathlib import Path

import numpy as np

from armenian_speech.speakers import Registry, SpeakerTracker
from scripts.check_speaker_decisions import CachedExtractor, segment, transform
from scripts.check_speakers import read_rows


def decide(registry, extractor, pcm, *, anchored=False, short=False, short_min=20000):
    vector = extractor.embed(pcm)
    full = registry.assign(vector, learn=False)
    if len(pcm) < 32000 and full['reason'] == 'match':
        return full
    probes = None
    if len(pcm) == 32000:
        probes = [extractor.embed(pcm[:16000]), extractor.embed(pcm[16000:])]
    elif short and len(pcm) >= short_min:
        # Overlapping views from this utterance only, not independent evidence.
        probes = [extractor.embed(pcm[:16000]), extractor.embed(pcm[-16000:])]
    consistent = probes is None or (all(v is not None for v in probes)
                                    and float(probes[0] @ probes[1]) >= registry.threshold)
    if not consistent:
        matches = [registry.assign(v, learn=False) for v in probes]
        if (anchored and full['reason'] == 'match'
                and all(m['reason'] == 'match' and m['label'] == full['label'] for m in matches)):
            return {**full, 'reason': 'anchored_match'}
        return {'label': 'Unknown', 'reason': 'inconsistent'}
    learn = len(pcm) == 32000 or (short and len(pcm) >= short_min)
    return registry.assign(vector, learn=learn)


def evaluate(jobs, extractor, **policy):
    registry = Registry(0.47)
    owners, first, duplicates, reasons = {}, {}, set(), Counter()
    unknown = wrong = mixed = duplicate_s = total = 0.0
    mixed_new = set()
    decisions = []
    for owner, pcm in jobs:
        # Quantize identically to the live PCM16 bridge.
        pcm = (pcm * 32768).astype('<i2').astype(np.float32) / 32768
        for start in range(0, len(pcm), 32000):
            cell = pcm[start:start + 32000]
            event = decide(registry, extractor, cell, **policy)
            label, seconds = event['label'], len(cell) / 16000
            total += seconds
            reasons[event['reason']] += 1
            if label == 'Unknown':
                unknown += seconds
            elif isinstance(owner, tuple):
                # Mixed source control: a single label does not separate both people.
                mixed += seconds
                if label not in owners:
                    owners[label] = None
                    mixed_new.add(label)
            else:
                if label not in owners:
                    owners[label] = owner
                    if owner in first:
                        duplicates.add(label)
                    first.setdefault(owner, label)
                if owners[label] != owner:
                    wrong += seconds
                elif first[owner] != label:
                    duplicate_s += seconds
            decisions.append({'owner': owner, **event, 'seconds': seconds})
    return {'clusters': len(registry.centroids), 'unknown_s': unknown, 'total_s': total,
            'wrong_person_s': wrong, 'mixed_single_label_s': mixed,
            'mixed_new_ids': sorted(mixed_new), 'duplicate_ids': sorted(duplicates),
            'duplicate_s': duplicate_s, 'reasons': dict(reasons), 'decisions': decisions}


def main():
    rows = read_rows()
    groups = {s: [r['pcm'] for r in rows if r['speaker'] == s and r['split'] == 'evaluation']
              for s in dict.fromkeys(r['speaker'] for r in rows)}
    speakers = list(groups)
    order = [(s, i) for i in range(4) for s in speakers]
    extractor = CachedExtractor()
    scenarios = {}
    for seconds in (1.0, 1.264, 1.52, 1.968, 2.0, 4.0):
        scenarios[f'clean_{seconds}s'] = [(s, groups[s][i][:int(seconds * 16000)])
                                          for s, i in order]
    enrollment = [(s, groups[s][0][:32000]) for s in speakers]
    for kind in ('gain', 'band', 'preroll'):
        scenarios[kind] = enrollment + [(s, transform(groups[s][i][:32000], kind))
                                        for s, i in order]
        scenarios[f'short_1.52_{kind}'] = enrollment + [
            (s, transform(groups[s][i][:24320], kind)) for s, i in order]
    a, b = speakers[:2]
    scenarios['mixed_AB_BA'] = enrollment + [
        ((a, b), np.concatenate((groups[a][i][:16000], groups[b][i][:16000])))
        for i in range(4)] + [
        ((b, a), np.concatenate((groups[b][i][:16000], groups[a][i][:16000])))
        for i in range(4)]
    scenarios['overlap_AB'] = enrollment + [
        ((a, b), (groups[a][i][:32000] + groups[b][i][:32000]) / 2) for i in range(4)]
    for seconds in (1.264, 1.52, 1.968):
        size = int(seconds * 16000)
        scenarios[f'short_mixed_{seconds}'] = enrollment + [
            ((a, b), np.concatenate((groups[a][i][:int(size * ratio)],
                                    groups[b][i][:size - int(size * ratio)])))
            for i in range(4) for ratio in (0.25, 0.5, 0.75)]
    results = {}
    for name, jobs in scenarios.items():
        results[name] = {}
        for policy, flags in {'baseline': {}, 'anchored': {'anchored': True},
                              'short': {'short': True},
                              'short_1.5': {'short': True, 'short_min': 24000},
                              'both_1.5': {'anchored': True, 'short': True, 'short_min': 24000},
                              'both': {'anchored': True, 'short': True}}.items():
            result = evaluate(jobs, extractor, **flags)
            results[name][policy] = result
            print(name, policy, json.dumps({k: v for k, v in result.items() if k != 'decisions'}))
        tracker, observed = SpeakerTracker(extractor), []
        for _, pcm in jobs:
            tracker.split(segment(pcm), on_decision=observed.append)
        expected = results[name]['baseline']['decisions']
        if [(d['label'], d['duration_s']) for d in observed] != [
                (d['label'], d['seconds']) for d in expected]:
            raise AssertionError('Offline baseline differs from live tracker')
        trial, trial_events = SpeakerTracker(extractor, experimental=True), []
        for _, pcm in jobs:
            trial.split(segment(pcm), on_decision=trial_events.append)
        if [(d['label'], d['duration_s']) for d in trial_events] != [
                (d['label'], d['seconds']) for d in results[name]['both_1.5']['decisions']]:
            raise AssertionError('Offline trial differs from live tracker')
    report = {'scope': 'Reused public English clips; synthetic controls, not call DER',
              'limitations': ['Overlapping short views are not independent evidence',
                              'No threshold fitting, no live policy change',
                              'Mixed/overlap assignment counts are control outcomes, not DER',
                              'Enrollment repeats some evaluation clips'],
              'baseline_labels_verified_against_live_tracker': True, 'scenarios': results}
    target = Path('reports/speaker_candidates_production_verified.json')
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

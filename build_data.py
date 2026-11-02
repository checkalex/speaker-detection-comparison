#!/usr/bin/env python3
"""Export only publication-safe measurements from an existing benchmark run."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def activity(segments, duration):
    events = {0.0: 0, duration: 0}
    for s in segments:
        events[s['start']] = events.get(s['start'], 0) + 1
        events[s['end']] = events.get(s['end'], 0) - 1
    count, result = 0, []
    points = sorted(events)
    for i, start in enumerate(points[:-1]):
        count += events[start]
        end = points[i + 1]
        if result and result[-1][2] == count and abs(result[-1][1] - start) < 1e-8:
            result[-1][1] = end
        else:
            result.append([start, end, count])
    assert all(c >= 0 for _, _, c in result)
    assert abs(sum(b - a for a, b, _ in result) - duration) < 1e-6
    return result


def overlap_stats(series, start, end):
    runs = [(max(a, start), min(b, end), count) for a, b, count in series if a < end and b > start]
    return {'seconds': sum(b - a for a, b, count in runs if count >= 2),
            'peak': max((count for _, _, count in runs), default=0)}


def union(intervals):
    result = []
    for a, b in sorted(intervals):
        if result and a <= result[-1][1] + 1e-8:
            result[-1][1] = max(result[-1][1], b)
        else:
            result.append([a, b])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    sys.path.insert(0, str(run.parent.parent))
    import bench
    scores = bench.generate_scores(run)
    public = {'date': '2026-11-02', 'scope': 'Five completed English animation and live-action recordings',
              'metric': 'Diarization error rate (DER)', 'collar_seconds': 0,
              'overlap_included': True, 'summary': {},
              'models': {
                  'pyannote': {'name': 'pyannote Precision-3', 'short': 'Precision-3', 'deployment': 'Hosted API',
                               'source': 'https://www.pyannote.ai/precision-3'},
                  'nemotron': {'name': 'NVIDIA Nemotron 3 Diarization', 'short': 'NVIDIA', 'deployment': 'Local RTX 4090',
                               'source': 'https://huggingface.co/nvidia/Nemotron-3-Diarization',
                               'speaker_limit': 8, 'threshold': .5,
                               'revision': bench.REVISION, 'transformers_commit': bench.TRANSFORMERS_COMMIT}},
              'clips': []}
    config = [('Dave_the_Barbarian', 'dave', 'Dave the Barbarian', 'A five-voice chorus', 'Singing, music and a large cast'),
              ('pizza_delivery', 'pizza', 'Pizza Delivery', 'Short exchanges & expressive voices', 'Rapid dialogue and background music'),
              ('Veronica_Having_Bad_Luck', 'veronica', 'Veronica Having Bad Luck', 'Frequent changes across eight roles', 'Short turns and similar character voices'),
              ('friends_funniest_moments_friends_export-', 'friends', 'Friends: Funniest Moments', 'Eight named characters', 'Live-action dialogue, laughter and long subtitle gaps'),
              ('friends_tv_show_-_christmas_episodes_compilation_pt_1_export-', 'christmas', 'Friends: Christmas Episodes', 'Nine named characters', 'Short interjections, laughter and a brief ninth speaker')]
    selected_scores = {model: [] for model in ['pyannote', 'nemotron']}
    for pattern, identifier, title, subtitle, context in config:
        paths = list((run / 'clips').glob(pattern + '*'))
        assert len(paths) == 1
        path = paths[0]
        meta = bench.read_json(path / 'meta.json')
        duration = meta['duration_seconds']
        reference = bench.read_reference(path / 'reference.csv', duration)
        clip = {'id': identifier, 'title': title, 'subtitle': subtitle, 'context': context,
                'duration': duration, 'speakers': len({s['speaker'] for s in reference}),
                'audio_sha256': meta['audio_sha256'], 'reference_sha256': hashlib.sha256((path / 'reference.csv').read_bytes()).hexdigest(),
                'model_assisted_reference': True,
                'initial_reference_source': 'NVIDIA-assisted labels' if identifier == 'christmas' else 'Checksub original export',
                'confirmed_overlap_reference': identifier == 'dave',
                'activity': {'reference': activity(reference, duration)}, 'results': {}}
        if identifier == 'christmas':
            clip['reference_note'] = ('Reviewed from an SRT prepared with NVIDIA speaker labels and existing Checksub cue times. '
                                      'This may favor NVIDIA’s measured agreement, including how well its output aligns with the reference. '
                                      'The cue times were inherited from Checksub and were not independently annotated.')
        else:
            clip['reference_note'] = ('Reviewed from Checksub’s original subtitle export and speaker assignments. '
                                      'This may favor agreement with the Checksub baseline represented here by Precision-3. '
                                      'Cue times came from Checksub’s transcription/alignment pipeline and were not independently annotated.')
        for detector in ['pyannote', 'nemotron']:
            result = bench.read_json(path / (detector + '.json'))
            assert result['audio_sha256'] == meta['audio_sha256']
            assert result['config'] == bench.expected_config(detector)
            score = next(r for r in scores['clips'] if r['clip'] == path.name and r['detector'] == detector)
            assert score['status'] == 'scored'
            selected_scores[detector].append(score)
            clip['activity'][detector] = activity(result['segments'], duration)
            clip['results'][detector] = {k: score[k] for k in ['der_percent', 'reference_speaker_seconds',
                'missed_speech_seconds', 'false_speech_seconds', 'speaker_confusion_seconds', 'detected_speakers']}
            clip['results'][detector]['overlap'] = overlap_stats(clip['activity'][detector], 0, duration)
        annotated = union([(a, b) for a, b, count in clip['activity']['reference'] if count >= 2])
        clip['annotated_overlap_seconds'] = sum(b - a for a, b in annotated)
        clip['overlap_events'] = []
        for a, b in annotated:
            clip['overlap_events'].append({'start': a, 'end': b, 'annotated': True,
                **{key: overlap_stats(series, a, b) for key, series in clip['activity'].items()}})
        predicted = union([(a, b) for detector in ['pyannote', 'nemotron']
                           for a, b, count in clip['activity'][detector] if count >= 2])
        for a, b in predicted:
            if any(a < q and b > p for p, q in annotated):
                continue
            clip['overlap_events'].append({'start': a, 'end': b, 'annotated': False,
                **{key: overlap_stats(series, a, b) for key, series in clip['activity'].items()}})
        clip['overlap_events'].sort(key=lambda e: e['start'])
        for detector in ['pyannote', 'nemotron']:
            clip['results'][detector]['annotated_overlap_detected_seconds'] = sum(
                overlap_stats(clip['activity'][detector], a, b)['seconds'] for a, b in annotated)
        public['clips'].append(clip)
    public['audio_seconds'] = sum(c['duration'] for c in public['clips'])
    within_limit = [c for c in public['clips'] if c['speakers'] <= 8]
    public['within_eight_speakers'] = {}
    for model in ['pyannote', 'nemotron']:
        total = sum(c['results'][model]['reference_speaker_seconds'] for c in within_limit)
        errors = sum(c['results'][model][key] for c in within_limit
                     for key in ['missed_speech_seconds', 'false_speech_seconds', 'speaker_confusion_seconds'])
        public['within_eight_speakers'][model] = {'clips': len(within_limit), 'der_percent': 100 * errors / total}
    public['aggregate_errors'] = {}
    for model in ['pyannote', 'nemotron']:
        total = sum(c['results'][model]['reference_speaker_seconds'] for c in public['clips'])
        public['aggregate_errors'][model] = {
            key: {'seconds': sum(c['results'][model][key] for c in public['clips']),
                  'der_points': 100 * sum(c['results'][model][key] for c in public['clips']) / total}
            for key in ['missed_speech_seconds', 'false_speech_seconds', 'speaker_confusion_seconds']}
        public['summary'][model] = {
            'paired_clips': len(public['clips']),
            'der_percent': sum(value['der_points'] for value in public['aggregate_errors'][model].values())}
        expected = sum(row['der_percent'] * row['reference_speaker_seconds'] for row in selected_scores[model]) / total
        assert abs(public['summary'][model]['der_percent'] - expected) < 1e-8
    target = Path(__file__).parent / 'site' / 'data'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'comparison.json').write_text(json.dumps(public, indent=2) + '\n')
    (target / 'comparison.js').write_text('window.COMPARISON = ' + json.dumps(public, separators=(',', ':')) + ';\n')
    # The webpage works both as a local file and under a GitHub Pages project path.
    import csv
    with (target / 'results.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['clip', 'model', 'DER_percent', 'reference_speakers', 'detected_speakers', 'missed_speech_seconds', 'false_speech_seconds', 'speaker_confusion_seconds'])
        for clip in public['clips']:
            for model in ['pyannote', 'nemotron']:
                score = clip['results'][model]
                writer.writerow([clip['title'], public['models'][model]['name'], score['der_percent'], clip['speakers'],
                                 score['detected_speakers'], score['missed_speech_seconds'], score['false_speech_seconds'], score['speaker_confusion_seconds']])
    print('Exported sanitized data:', target)
    print('Audio duration:', public['audio_seconds'], 'seconds')
    for clip in public['clips']:
        print(clip['title'], 'annotated overlap:', clip['annotated_overlap_seconds'], 'seconds; events:', len(clip['overlap_events']))


if __name__ == '__main__':
    main()

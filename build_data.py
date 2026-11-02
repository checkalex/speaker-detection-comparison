#!/usr/bin/env python3
"""Export only publication-safe measurements from an existing benchmark run."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import subtitle_accuracy


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
    subtitle_scores = []
    subtitle_audit = []
    for pattern, identifier, title, subtitle, context in config:
        paths = list((run / 'clips').glob(pattern + '*'))
        assert len(paths) == 1
        path = paths[0]
        meta = bench.read_json(path / 'meta.json')
        duration = meta['duration_seconds']
        reference = bench.read_reference(path / 'reference.csv', duration)
        reference_cues = subtitle_accuracy.read_cues(path / 'reference.csv', duration)
        clip = {'id': identifier, 'title': title, 'subtitle': subtitle, 'context': context,
                'duration': duration, 'speakers': len({s['speaker'] for s in reference}),
                'audio_sha256': meta['audio_sha256'], 'reference_sha256': hashlib.sha256((path / 'reference.csv').read_bytes()).hexdigest(),
                'model_assisted_reference': True,
                'initial_reference_source': 'NVIDIA-assisted labels' if identifier == 'christmas' else 'Checksub original export',
                'confirmed_overlap_reference': identifier == 'dave',
                'activity': {'reference': activity(reference, duration)}, 'results': {}}
        if identifier == 'christmas':
            clip['reference_note'] = ('Reviewed from an SRT prepared with NVIDIA speaker labels and existing Checksub cue times. '
                                      'The initial labels may favor NVIDIA’s measured identity agreement through review anchoring. '
                                      'The cue times were inherited from Checksub, shared by both models and were not independently annotated.')
        else:
            clip['reference_note'] = ('Reviewed from Checksub’s original subtitle export and speaker assignments. '
                                      'The initial speaker labels may influence human review. '
                                      'Cue times came from the shared Checksub transcription/alignment pipeline; those times do not inherently favor either diarizer.')
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
            fallback = 'SPEAKER_00' if detector == 'pyannote' else 'speaker_0'
            cue_score = subtitle_accuracy.score_cues(reference_cues, result['segments'], fallback)
            clip['results'][detector]['subtitle_accuracy'] = cue_score['summary']
            subtitle_scores.append({'clip': identifier, 'title': title, 'model': detector, **cue_score})
            anonymous_reference = {name: f'R{index + 1}' for index, name in enumerate(sorted({
                name for cue in reference_cues for name in cue['speakers']}))}
            for cue in cue_score['cues']:
                subtitle_audit.append({'clip': title, 'model': detector, 'cue_number': cue['cue_number'],
                    'start': cue['start'], 'end': cue['end'],
                    'reference_speakers': '|'.join(anonymous_reference[name] for name in cue['speakers']),
                    'predicted_cluster': cue['predicted_speaker'],
                    'mapped_reference': anonymous_reference.get(cue['mapped_speaker']),
                    'status': cue['status'], 'correct': cue['correct'], 'editor_fallback': cue['fallback']})
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
    public['subtitle_accuracy_method'] = {
        'unit': 'One reviewed subtitle line; every line has equal weight',
        'assignment': 'Checksub Subtitles::SetSpeakers: largest single segment overlap; first segment wins ties; no overlap defaults to speaker ID 1',
        'mapping': 'One global one-to-one cluster-to-reference mapping per recording and model, maximizing correct line count',
        'excluded': 'Lines with more than one annotated speaker are excluded from this single-speaker metric and remain in DER/overlap evaluation',
        'fallback': 'Primary accuracy includes Checksub default-speaker assignments; supported accuracy counts correct lines only when a model segment overlaps',
        'interpretation': 'Best-case speaker grouping agreement after consistent cluster naming; a proxy for speaker-label corrections, not measured editing time'
    }
    public['subtitle_accuracy_summary'] = {}
    for subset, clips in [('all', public['clips']), ('without_christmas', [c for c in public['clips'] if c['id'] != 'christmas']),
                          ('within_eight_speakers', [c for c in public['clips'] if c['speakers'] <= 8])]:
        public['subtitle_accuracy_summary'][subset] = {
            model: subtitle_accuracy.aggregate([c['results'][model]['subtitle_accuracy'] for c in clips])
            for model in ['pyannote', 'nemotron']}
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
    bench.write_json(run / 'subtitle-scores.json', {
        'method': public['subtitle_accuracy_method'], 'summary': public['subtitle_accuracy_summary'], 'clips': subtitle_scores})
    (target / 'comparison.json').write_text(json.dumps(public, indent=2) + '\n')
    (target / 'comparison.js').write_text('window.COMPARISON = ' + json.dumps(public, separators=(',', ':')) + ';\n')
    # The webpage works both as a local file and under a GitHub Pages project path.
    import csv
    with (target / 'subtitle-assignments.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(subtitle_audit[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(subtitle_audit)
    with (target / 'subtitle-accuracy.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['clip', 'model', *public['subtitle_accuracy_summary']['all']['pyannote']], lineterminator='\n')
        writer.writeheader()
        for clip in public['clips']:
            for model in ['pyannote', 'nemotron']:
                writer.writerow({'clip': clip['title'], 'model': public['models'][model]['name'],
                                 **clip['results'][model]['subtitle_accuracy']})
        for subset, models in public['subtitle_accuracy_summary'].items():
            for model, summary in models.items():
                writer.writerow({'clip': subset, 'model': public['models'][model]['name'], **summary})
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

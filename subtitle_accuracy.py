"""Score cached diarization as Checksub subtitle speaker assignments, without inference."""
import csv
import math


def read_cues(path, duration):
    """Keep individual subtitle boundaries; group simultaneous reference speakers."""
    grouped = {}
    with open(path, newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ['start', 'end', 'speaker']:
            raise ValueError('Expected reference CSV header start,end,speaker')
        for row in reader:
            if not any(row.values()):
                continue
            start, end, speaker = float(row['start']), float(row['end']), row['speaker'].strip()
            if not all(math.isfinite(t) for t in [start, end]) or start < 0 or end <= start or end > duration + .1 or not speaker:
                raise ValueError('Invalid reference subtitle interval')
            grouped.setdefault((start, min(end, duration)), set()).add(speaker)
    if not grouped:
        raise ValueError('Reference is empty')
    return [{'cue_number': number, 'start': start, 'end': end, 'speakers': sorted(speakers)}
            for number, ((start, end), speakers) in enumerate(grouped.items(), 1)]


def assign_cue(cue, segments, fallback):
    """Mirror Subtitles::SetSpeakers: largest SINGLE overlap, first on ties, default ID 1."""
    selected, greatest = None, 0
    for segment in segments:
        if segment['end'] <= cue['start']:
            continue
        if segment['start'] >= cue['end']:
            break
        overlap = (min(segment['end'], cue['end']) - max(segment['start'], cue['start'])) / (cue['end'] - cue['start'])
        if selected is None or overlap > greatest:
            selected, greatest = segment['speaker'], overlap
    return (selected if selected is not None else fallback), selected is None


def score_cues(cues, segments, fallback):
    """Best global one-to-one identity mapping, optimized for the number of correct lines."""
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    previous_start = -math.inf
    for segment in segments:
        start, end = segment['start'], segment['end']
        if not all(math.isfinite(t) for t in [start, end]) or start < 0 or end <= start or start < previous_start or not segment['speaker']:
            raise ValueError('Speaker intervals must be valid and ordered by start time')
        previous_start = start

    assignments = []
    for cue in cues:
        if len(cue['speakers']) != 1:
            assignments.append({**cue, 'status': 'excluded_multiple_speakers', 'correct': None,
                                'predicted_speaker': None, 'mapped_speaker': None, 'fallback': False})
            continue
        prediction, used_fallback = assign_cue(cue, segments, fallback)
        assignments.append({**cue, 'status': 'scored', 'predicted_speaker': prediction, 'fallback': used_fallback})

    scored = [row for row in assignments if row['status'] == 'scored']
    reference_labels = sorted({row['speakers'][0] for row in scored})
    predicted_labels = sorted({row['predicted_speaker'] for row in scored})
    ref_index = {label: i for i, label in enumerate(reference_labels)}
    pred_index = {label: i for i, label in enumerate(predicted_labels)}
    matrix = np.zeros((len(predicted_labels), len(reference_labels)), dtype=int)
    for row in scored:
        matrix[pred_index[row['predicted_speaker']], ref_index[row['speakers'][0]]] += 1
    mapping = {}
    if matrix.size:
        predictions, references = linear_sum_assignment(matrix, maximize=True)
        mapping = {predicted_labels[p]: reference_labels[r] for p, r in zip(predictions, references) if matrix[p, r] > 0}
    for row in scored:
        row['mapped_speaker'] = mapping.get(row['predicted_speaker'])
        row['correct'] = row['mapped_speaker'] == row['speakers'][0]

    correct = sum(row['correct'] for row in scored)
    fallbacks = [row for row in scored if row['fallback']]
    fallback_correct = sum(row['correct'] for row in fallbacks)
    count = len(scored)
    summary = {'total_cues': len(cues), 'scored_cues': count,
               'excluded_multiple_speaker_cues': len(cues) - count,
               'correct_cues': correct, 'incorrect_cues': count - correct,
               'accuracy_percent': 100 * correct / count if count else None,
               'fallback_cues': len(fallbacks), 'fallback_correct_cues': fallback_correct,
               'supported_correct_cues': correct - fallback_correct,
               'supported_accuracy_percent': 100 * (correct - fallback_correct) / count if count else None}
    return {'summary': summary, 'mapping': mapping, 'cues': assignments}


def aggregate(results):
    keys = ['total_cues', 'scored_cues', 'excluded_multiple_speaker_cues', 'correct_cues',
            'incorrect_cues', 'fallback_cues', 'fallback_correct_cues', 'supported_correct_cues']
    summary = {key: sum(result[key] for result in results) for key in keys}
    count = summary['scored_cues']
    summary['accuracy_percent'] = 100 * summary['correct_cues'] / count if count else None
    summary['supported_accuracy_percent'] = 100 * summary['supported_correct_cues'] / count if count else None
    return summary

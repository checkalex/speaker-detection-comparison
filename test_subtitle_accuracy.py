import tempfile
from pathlib import Path
import unittest

from subtitle_accuracy import aggregate, assign_cue, read_cues, score_cues


def cue(start, end, *speakers):
    return {'start': start, 'end': end, 'speakers': list(speakers)}


def turn(start, end, speaker):
    return {'start': start, 'end': end, 'speaker': speaker}


class SubtitleAccuracyTests(unittest.TestCase):
    def test_preserves_adjacent_lines_and_groups_multiple_reference_speakers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reference.csv'
            path.write_text('start,end,speaker\n0,1,Alice\n1,2,Alice\n2,3,Alice\n2,3,Bob\n')
            cues = read_cues(path, 3)
        result = score_cues(cues, [turn(0, 3, 'x')], 'x')
        self.assertEqual(len(cues), 3)
        self.assertEqual(result['summary']['scored_cues'], 2)
        self.assertEqual(result['summary']['excluded_multiple_speaker_cues'], 1)
        self.assertEqual(result['summary']['correct_cues'], 2)

    def test_uses_longest_individual_overlap_instead_of_summing_same_speaker(self):
        segments = [turn(0, 2, 'x'), turn(2, 5, 'y'), turn(5, 7, 'x')]
        self.assertEqual(assign_cue(cue(0, 7, 'Alice'), segments, 'x'), ('y', False))
        self.assertEqual(assign_cue(cue(0, 4, 'Alice'), segments, 'x'), ('x', False))
        self.assertEqual(assign_cue(cue(7, 8, 'Alice'), segments, 'x'), ('x', True))

    def test_arbitrary_ids_use_one_mapping_for_the_entire_recording(self):
        cues = [cue(0, 1, 'Alice'), cue(1, 2, 'Bob'), cue(2, 3, 'Alice'), cue(3, 4, 'Bob')]
        segments = [turn(0, 1, 'z'), turn(1, 2, 'x'), turn(2, 3, 'z'), turn(3, 4, 'x')]
        result = score_cues(cues, segments, 'x')
        self.assertEqual(result['mapping'], {'x': 'Bob', 'z': 'Alice'})
        self.assertEqual(result['summary']['accuracy_percent'], 100)

    def test_merging_or_splitting_identities_requires_corrections(self):
        cues = [cue(0, 1, 'Alice'), cue(1, 2, 'Bob')]
        merged = score_cues(cues, [turn(0, 2, 'x')], 'x')
        split = score_cues([cue(0, 1, 'Alice'), cue(1, 2, 'Alice')],
                           [turn(0, 1, 'x'), turn(1, 2, 'y')], 'x')
        self.assertEqual(merged['summary']['accuracy_percent'], 50)
        self.assertEqual(split['summary']['accuracy_percent'], 50)
        self.assertEqual(len(split['mapping']), 1)

    def test_mapping_maximizes_correct_lines_rather_than_longest_line_duration(self):
        cues = [cue(0, 100, 'Alice'), cue(100, 101, 'Bob'), cue(101, 102, 'Bob')]
        result = score_cues(cues, [turn(0, 102, 'x')], 'x')
        self.assertEqual(result['mapping'], {'x': 'Bob'})
        self.assertEqual(result['summary']['correct_cues'], 2)

    def test_editor_fallback_is_reported_separately_from_supported_assignments(self):
        result = score_cues([cue(0, 1, 'Alice'), cue(1, 2, 'Alice')], [turn(0, 1, 'zero')], 'zero')
        self.assertEqual(result['summary']['accuracy_percent'], 100)
        self.assertEqual(result['summary']['supported_accuracy_percent'], 50)
        self.assertEqual(result['summary']['fallback_cues'], 1)
        self.assertEqual(result['summary']['fallback_correct_cues'], 1)

    def test_empty_detector_output_does_not_look_like_successful_detection(self):
        result = score_cues([cue(0, 1, 'Alice'), cue(1, 2, 'Bob')], [], 'zero')
        self.assertEqual(result['summary']['fallback_cues'], 2)
        self.assertEqual(result['summary']['accuracy_percent'], 50)
        self.assertEqual(result['summary']['supported_accuracy_percent'], 0)

    def test_invalid_inputs_fail_and_empty_scoring_is_not_perfect(self):
        for segments in [[turn(2, 1, 'x')], [turn(1, 2, 'x'), turn(0, 1, 'y')]]:
            with self.assertRaises(ValueError):
                score_cues([cue(0, 2, 'Alice')], segments, 'x')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reference.csv'
            for text in ['start,end,speaker\n', 'start,end,speaker\n1,0,Alice\n', 'start,end,speaker\n0,1,\n']:
                path.write_text(text)
                with self.assertRaises(ValueError):
                    read_cues(path, 2)
        self.assertIsNone(score_cues([cue(0, 1, 'Alice', 'Bob')], [], 'x')['summary']['accuracy_percent'])

    def test_aggregate_counts_lines_instead_of_averaging_clip_percentages(self):
        short = score_cues([cue(0, 1, 'Alice')], [turn(0, 1, 'x')], 'x')['summary']
        long = score_cues([cue(i, i + 1, str(i)) for i in range(9)], [turn(0, 9, 'x')], 'x')['summary']
        result = aggregate([short, long])
        self.assertEqual(result['scored_cues'], 10)
        self.assertEqual(result['correct_cues'], 2)
        self.assertEqual(result['accuracy_percent'], 20)


if __name__ == '__main__':
    unittest.main()

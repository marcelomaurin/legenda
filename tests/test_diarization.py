import unittest

from bin.diarize_session import assign_speakers, extract_turns


class Segment:
    def __init__(self, start, end):
        self.start = start
        self.end = end


class Annotation:
    def itertracks(self, yield_label=False):
        self.assert_yield_label = yield_label
        yield Segment(0.0, 1.0), "track-1", "SPEAKER_00"
        yield Segment(1.0, 2.0), "track-2", "SPEAKER_01"


class DiarizationTests(unittest.TestCase):
    def test_extract_turns_from_annotation(self):
        turns = extract_turns(Annotation())
        self.assertEqual(turns, [
            (0, 1000, "SPEAKER_00"),
            (1000, 2000, "SPEAKER_01"),
        ])

    def test_assigns_by_largest_overlap(self):
        events = [{"start_ms": 800, "end_ms": 1400}]
        turns = [
            (0, 1000, "A"),
            (1000, 2000, "B"),
        ]
        result = assign_speakers(events, turns)
        self.assertEqual(result[0]["speaker"], "B")

    def test_no_overlap_leaves_speaker_none(self):
        events = [{"start_ms": 3000, "end_ms": 3500}]
        turns = [(0, 1000, "A")]
        result = assign_speakers(events, turns)
        self.assertIsNone(result[0]["speaker"])


if __name__ == "__main__":
    unittest.main()

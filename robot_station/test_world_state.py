import unittest
from world_state import WorldState, visibility_answer


def frame(stamp, name='Sam Jacob', state='ready', score=0.7):
    objects = [] if name is False else [{'label': 'person', 'confidence': 0.9,
        'identity': {'name': name, 'similarity': score} if name else None}]
    return {'header': {'stamp': {'sec': int(stamp), 'nanosec': int((stamp % 1) * 1e9)}},
            'recognition_state': state, 'objects': objects}


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.world = WorldState()
        self.memory = {'available': True, 'people': ['Sam Jacob']}

    def answer(self, prompt='Can you see Sam?', wall=101, mono=11):
        return visibility_answer(prompt, self.memory, self.world.snapshot(wall, mono))

    def confirm(self):
        self.world.update(frame(100), 100, 10)
        self.world.update(frame(101), 101, 11)

    def test_enrollment_without_camera_is_not_visibility(self):
        self.assertIn("can't tell", self.answer())

    def test_single_frame_only_possible_match(self):
        self.world.update(frame(101), 101, 11)
        self.assertIn('possible match', self.answer())

    def test_consecutive_frames_confirm(self):
        self.confirm()
        self.assertIn('recognized Sam Jacob', self.answer())
        self.assertIn('recognized Sam Jacob', self.answer('Can you see Sam right now?'))
        self.assertIn('recognized Sam Jacob', self.answer('Is Sam visible now?'))

    def test_stale_frame_cannot_claim_current_visibility(self):
        self.confirm()
        self.assertIn("can't tell", self.answer(wall=105, mono=15))
        self.assertIn('last confirmed', self.answer(wall=105, mono=15))

    def test_empty_frame_clears_current_identity(self):
        self.confirm()
        self.world.update(frame(102, False), 102, 12)
        self.assertIn('do not currently recognize', self.answer(wall=102, mono=12))
        self.assertIn('last recognized', self.answer('When did you last see Sam?', 102, 12))

    def test_unhealthy_recognition_rejects_names(self):
        self.world.update(frame(100, state='database_unavailable'), 100, 10)
        self.world.update(frame(101, state='database_unavailable'), 101, 11)
        self.assertIn('recognition is unavailable', self.answer())

    def test_low_similarity_not_named(self):
        self.world.update(frame(100, score=0.2), 100, 10)
        self.world.update(frame(101, score=0.2), 101, 11)
        self.assertEqual(self.world.snapshot(101, 11)['confirmed_names'], [])

    def test_replay_cannot_confirm(self):
        self.world.update(frame(100), 100, 10)
        self.assertFalse(self.world.update(frame(100), 101, 11))
        self.assertEqual(self.world.snapshot(101, 11)['confirmed_names'], [])

    def test_old_future_and_invalid_frames_rejected(self):
        for data in [frame(90), frame(105), {}, frame(101, score=float('nan'))]:
            self.world.update(data, 101, 11)
        self.assertEqual(self.world.snapshot(101, 11)['confirmed_names'], [])

    def test_revoked_name_not_claimed(self):
        self.confirm()
        self.memory['people'] = []
        self.assertIn('no matching enrolled', self.answer())

    def test_monotonic_expiry_even_if_wall_clock_moves_back(self):
        self.confirm()
        self.assertFalse(self.world.snapshot(101, 20)['fresh'])

    def test_unknown_person_is_generic(self):
        self.world.update(frame(101, None), 101, 11)
        self.assertIn('1 person(s)', self.answer('Who can you see?'))
        self.assertIn('No enrolled identity', self.answer('Who can you see?'))

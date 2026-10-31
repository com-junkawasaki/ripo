import unittest
from analyze_live_pilot import summarize_trials


class LiveAnalysisControls(unittest.TestCase):
    def test_empty_and_partial_are_not_qualified_improvement(self):
        self.assertIsNone(summarize_trials([])['descriptive_latency_reduction_pct'])
        rows = [{'terminal': {'event': 'complete'}, 'results': [
            {'cache_prompt': mode, 'seconds': seconds, 'quality_pass': True, 'violations': []}]
        } for mode, seconds in [(None, 10), (True, 5)]]
        r = summarize_trials(rows)
        self.assertEqual(r['status'], 'stopped_early')
        self.assertEqual(r['descriptive_latency_reduction_pct'], 50)
        self.assertIsNone(r['qualified_awai_improvement_pct'])

    def test_http_completion_without_quality_is_not_accepted(self):
        with self.assertRaisesRegex(ValueError, 'quality-accepted'):
            summarize_trials([{'terminal': {'event': 'complete'}, 'results': [{'quality_pass': False}]}])

"""Focused queue checks, including future sequential snapshots without source-code edits."""
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from check_research_queue import check_queue


class ResearchQueueTests(unittest.TestCase):
    def setUp(self):
        self.text = (HERE.parents[1] / 'docs/evidence-program/research/research-session-review-queue.md').read_text()

    def test_current_counts(self):
        r = check_queue(self.text)
        self.assertEqual((r['research_queue_reviews_integrated_at_snapshot'], r['research_queue_reviews_prepared_at_snapshot'], r['research_queue_reviews_queued_at_snapshot']), (3, 1, 22))

    def test_future_sequential_snapshot_needs_no_checker_edit(self):
        s = self.text.replace('| Review prepared; integration pending |', '| Review integrated |').replace('| 5 | Concentration and shared dependencies | Queued |', '| 5 | Concentration and shared dependencies | Review prepared; integration pending |').replace('3 integrated; 1 prepared or awaiting CI; 22 queued.', '4 integrated; 1 prepared or awaiting CI; 21 queued.')
        self.assertEqual(check_queue(s)['research_queue_reviews_integrated_at_snapshot'], 4)

    def test_awaiting_ci_is_active_not_integrated(self):
        s=self.text.replace('| Review prepared; integration pending |', '| Awaiting CI |')
        self.assertEqual(check_queue(s)['research_queue_reviews_integrated_at_snapshot'], 3)

    def test_summary_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'summary/status'):
            check_queue(self.text.replace('3 integrated; 1 prepared', '4 integrated; 1 prepared'))

    def test_out_of_order_promotion_rejected(self):
        with self.assertRaisesRegex(ValueError, 'out-of-order'):
            check_queue(self.text.replace('| 6 | Historical capability backfills | Queued |', '| 6 | Historical capability backfills | Review integrated |'))

    def test_two_active_sessions_rejected(self):
        with self.assertRaisesRegex(ValueError, 'out-of-order'):
            check_queue(self.text.replace('| 5 | Concentration and shared dependencies | Queued |', '| 5 | Concentration and shared dependencies | Awaiting CI |'))

    def test_unknown_status_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            check_queue(self.text.replace('| Review prepared; integration pending |', '| Done |'))

    def test_swapped_titles_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identities'):
            check_queue(self.text.replace('Historical capability backfills', 'Other historical work'))


if __name__ == '__main__':
    unittest.main()

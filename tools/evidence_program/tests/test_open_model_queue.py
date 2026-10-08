"""Queue regressions use a synthetic snapshot, independent of review progress."""
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from check_research_queue import check_queue, EXPECTED_TITLES


def synthetic_snapshot(integrated=3, active=1):
    lines = ['Status snapshot: 8 October 2026, 00:00 UTC.',
             f'Snapshot counts: {integrated} integrated; {active} prepared or awaiting CI; {26-integrated-active} queued.']
    for i, title in enumerate(EXPECTED_TITLES, 1):
        status = 'Review integrated' if i <= integrated else ('Review prepared; integration pending' if i <= integrated+active else 'Queued')
        lines.append(f'| {i} | {title} | {status} | Synthetic test only |')
    return '\n'.join(lines)


class ResearchQueueTests(unittest.TestCase):
    def setUp(self):
        self.text = synthetic_snapshot()

    def test_current_repository_snapshot_is_consistent(self):
        text = (HERE.parents[1] / 'docs/evidence-program/research/research-session-review-queue.md').read_text()
        r = check_queue(text)
        self.assertEqual(sum(r[k] for k in ('research_queue_reviews_integrated_at_snapshot', 'research_queue_reviews_prepared_at_snapshot', 'research_queue_reviews_queued_at_snapshot')), 26)

    def test_synthetic_counts(self):
        r = check_queue(self.text)
        self.assertEqual((r['research_queue_reviews_integrated_at_snapshot'], r['research_queue_reviews_prepared_at_snapshot'], r['research_queue_reviews_queued_at_snapshot']), (3, 1, 22))

    def test_future_sequential_snapshots_need_no_checker_edit(self):
        for integrated in range(26):
            with self.subTest(integrated=integrated):
                self.assertEqual(check_queue(synthetic_snapshot(integrated))['research_queue_reviews_integrated_at_snapshot'], integrated)
        self.assertEqual(check_queue(synthetic_snapshot(26, 0))['research_queue_reviews_queued_at_snapshot'], 0)

    def test_awaiting_ci_is_active_not_integrated(self):
        s = self.text.replace('| Review prepared; integration pending |', '| Awaiting CI |')
        self.assertEqual(check_queue(s)['research_queue_reviews_integrated_at_snapshot'], 3)

    def test_summary_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'summary/status'):
            check_queue(self.text.replace('3 integrated; 1 prepared', '4 integrated; 1 prepared'))

    def test_out_of_order_promotion_rejected(self):
        with self.assertRaisesRegex(ValueError, 'out-of-order'):
            check_queue(self.text.replace('| 6 | Historical capability backfills | Queued |', '| 6 | Historical capability backfills | Review integrated |'))

    def test_contiguous_prepared_batch_is_accepted(self):
        r = check_queue(synthetic_snapshot(16, 4))
        self.assertEqual((r['research_queue_reviews_integrated_at_snapshot'],
                          r['research_queue_reviews_prepared_at_snapshot'],
                          r['research_queue_reviews_queued_at_snapshot']), (16, 4, 6))

    def test_contiguous_mixed_prepared_and_ci_batch_is_accepted(self):
        s = synthetic_snapshot(16, 4).replace(
            '| 18 | Claim-to-result provenance | Review prepared; integration pending |',
            '| 18 | Claim-to-result provenance | Awaiting CI |')
        self.assertEqual(check_queue(s)['research_queue_reviews_prepared_at_snapshot'], 4)

    def test_gap_in_prepared_batch_rejected(self):
        s = synthetic_snapshot(16, 4).replace(
            '| 18 | Claim-to-result provenance | Review prepared; integration pending |',
            '| 18 | Claim-to-result provenance | Queued |')
        with self.assertRaisesRegex(ValueError, 'out-of-order'):
            check_queue(s)

    def test_integrated_row_inside_prepared_batch_rejected(self):
        s = synthetic_snapshot(16, 4).replace(
            '| 18 | Claim-to-result provenance | Review prepared; integration pending |',
            '| 18 | Claim-to-result provenance | Review integrated |')
        with self.assertRaisesRegex(ValueError, 'out-of-order'):
            check_queue(s)

    def test_batch_promotion_without_updated_counts_rejected(self):
        s = synthetic_snapshot(16, 4).replace(
            '| 17 | Inference cost and price–performance | Review prepared; integration pending |',
            '| 17 | Inference cost and price–performance | Review integrated |')
        with self.assertRaisesRegex(ValueError, 'summary/status'):
            check_queue(s)

    def test_prepared_batch_at_queue_boundaries(self):
        for integrated, active in ((0, 4), (22, 4), (0, 26), (26, 0)):
            with self.subTest(integrated=integrated, active=active):
                r = check_queue(synthetic_snapshot(integrated, active))
                self.assertEqual(r['research_queue_reviews_prepared_at_snapshot'], active)

    def test_unknown_status_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            check_queue(self.text.replace('| Review prepared; integration pending |', '| Done |'))

    def test_swapped_titles_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identities'):
            check_queue(self.text.replace('Historical capability backfills', 'Other historical work'))


if __name__ == '__main__':
    unittest.main()

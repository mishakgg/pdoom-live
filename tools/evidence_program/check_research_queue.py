"""Offline consistency of the dated 26-session queue, including publication batches."""
from __future__ import annotations
import re

EXPECTED_TITLES = ('Chinese safety evaluations', 'Real-world adoption and productivity', 'Organizational safety practices', 'Open-model diffusion and accessibility', 'Concentration and shared dependencies', 'Historical capability backfills', 'AI-assisted scientific progress', 'Persuasion and information ecosystems', 'Robotics and physical-world capability', 'Training-data availability and feedback loops', 'Human reliance and decision quality', 'Algorithmic efficiency and scaling', 'Agent autonomy/security evaluations and incidents/near-misses', 'Labor-market effects and skill demand', 'Forecast and survey reconstruction', 'Incidents and near-misses', 'Inference cost and price–performance', 'Claim-to-result provenance', 'Model identity and retirement histories', 'Undercovered languages and regions', 'Mitigation effectiveness', 'Negative results and replications', 'Compute supply-chain bottlenecks', 'Chinese governance in practice', 'Benchmark drift and contamination', 'Electricity and deployment bottlenecks')
STATUS_RANK = {'Review integrated': 0, 'Review prepared; integration pending': 1,
               'Awaiting CI': 1, 'Queued': 2}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_queue(markdown):
    require(re.search(r'^Status snapshot: .+\d{4}.+UTC\.', markdown, re.MULTILINE),
            'Research queue must be a dated snapshot')
    rows = re.findall(r'^\| (\d+) \| ([^|]+) \| ([^|]+) \|', markdown, re.MULTILINE)
    require(len(rows) == 26 and [int(r[0]) for r in rows] == list(range(1, 27)),
            'Research queue must preserve 26 ordered sessions')
    require(tuple(r[1].strip() for r in rows) == EXPECTED_TITLES,
            'Research queue must preserve session identities and arrival order')
    statuses = [r[2].strip() for r in rows]
    require(all(s in STATUS_RANK for s in statuses), 'Unknown research queue status')
    ranks = [STATUS_RANK[s] for s in statuses]
    # Substantive reviews remain ordered; several reviewed sessions may await one
    # publication batch. Integrated, prepared and queued blocks stay contiguous.
    require(ranks == sorted(ranks),
            'Research queue cannot promote unfinished or out-of-order sessions')
    counts = (ranks.count(0), ranks.count(1), ranks.count(2))
    summary = re.findall(r'^Snapshot counts: (\d+) integrated; (\d+) prepared or awaiting CI; (\d+) queued\.$',
                         markdown, re.MULTILINE)
    require(len(summary) == 1 and tuple(map(int, summary[0])) == counts,
            'Research queue summary/status mismatch; cannot promote unfinished sessions')
    return {'research_queue_sessions': 26,
            'research_queue_reviews_integrated_at_snapshot': counts[0],
            'research_queue_reviews_prepared_at_snapshot': counts[1],
            'research_queue_reviews_queued_at_snapshot': counts[2]}

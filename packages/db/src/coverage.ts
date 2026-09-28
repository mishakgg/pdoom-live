export function staleApprovalSql(statementAlias = "s"): string {
  return `EXISTS (
    SELECT 1
    FROM review_decisions stale_d
    JOIN source_items stale_si ON stale_si.id = ${statementAlias}.source_item_id
    JOIN evidence_segments stale_e ON stale_e.id = ${statementAlias}.evidence_segment_id
    WHERE stale_d.statement_id = ${statementAlias}.id
      AND (stale_d.reviewed_at, stale_d.decision_key) = (
        SELECT d2.reviewed_at, d2.decision_key
        FROM review_decisions d2
        WHERE d2.statement_id = ${statementAlias}.id
        ORDER BY d2.reviewed_at DESC, d2.decision_key DESC
        LIMIT 1
      )
      AND (
        stale_d.resulting_review_state <> 'human_verified'
        OR stale_d.source_content_hash <> stale_si.content_hash
        OR stale_d.evidence_hash <> stale_e.segment_hash
        OR stale_d.content_version <> stale_si.content_version
      )
  )`;
}

export function effectiveReviewStateSql(statementAlias = "s"): string {
  return `CASE WHEN ${statementAlias}.review_state = 'human_verified' AND ${staleApprovalSql(statementAlias)} THEN 'needs_review' ELSE ${statementAlias}.review_state END`;
}

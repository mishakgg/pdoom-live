import { PUBLIC_REVIEW_STATES } from "@pdoom/contracts";
import { effectiveReviewStateSql } from "./coverage";

/** Website pages include unsettled needs_review records; research/indexing do not. */
export function websiteReviewSql(column: string): string {
  return `${column} IN (${PUBLIC_REVIEW_STATES.map((state) => `'${state}'`).join(", ")})`;
}

/** Public provenance has one item locator/hash; its evidence must belong to that item.
 * Independent database FKs/import slugs do not guarantee this relationship.
 */
export function statementEvidenceMatchesItemSql(statementAlias = "s"): string {
  return `EXISTS (
    SELECT 1 FROM evidence_segments publication_e
    WHERE publication_e.id = ${statementAlias}.evidence_segment_id
      AND publication_e.source_item_id = ${statementAlias}.source_item_id
  )`;
}

/** A source rejection overrides a statement's review state; removal does not. */
export function websiteStatementSql(statementAlias = "s"): string {
  return `(${websiteReviewSql(effectiveReviewStateSql(statementAlias))} AND ${statementEvidenceMatchesItemSql(statementAlias)} AND EXISTS (
    SELECT 1 FROM source_items visible_si
    JOIN sources visible_src ON visible_src.id = visible_si.source_id
    WHERE visible_si.id = ${statementAlias}.source_item_id AND visible_src.review_state <> 'rejected'
  ))`;
}

/** Unreviewed containers are exact audit targets only after a statement is public. */
export function websiteSourceAuditSql(sourceAlias = "src"): string {
  return `(${websiteReviewSql(`${sourceAlias}.review_state`)} OR (
    ${sourceAlias}.review_state = 'unreviewed' AND EXISTS (
      SELECT 1 FROM source_items audit_si
      WHERE audit_si.source_id = ${sourceAlias}.id AND ${websiteSourceItemSql("audit_si")}
    )
  ))`;
}

/** Items have no review state. Only a public statement makes their evidence public.
 * Do not require is_current or availability: historical/removed evidence is an audit target.
 */
export function websiteSourceItemSql(itemAlias = "si"): string {
  return `EXISTS (
    SELECT 1 FROM statements visible_s
    WHERE visible_s.source_item_id = ${itemAlias}.id
      AND ${websiteStatementSql("visible_s")}
  )`;
}

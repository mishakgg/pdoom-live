import { sha256, stableId } from "../packages/db/src/ids";
import type pg from "pg";

const speaker = stableId("person:searchfix-speaker");
const other = stableId("person:searchfix-other");
const org = stableId("organization:searchfix-org");
const source = stableId("source:searchfix-source");
const item = stableId("source_item:searchfix-item");
const topic = stableId("topic:searchfix-agi-2030");
const affiliation = stableId("affiliation:searchfix-private");
const rejectedAffiliation = stableId("affiliation:searchfix-rejected-role");

const statements = [
  ["searchfix-agi-new", "explicit_numeric", "Fixture AGI 2030 point estimate from the newer note.", "2024-06-01T12:00:00Z", "human_verified"],
  ["searchfix-agi-qual", "explicit_qualitative", "Fixture AGI 2030 was called plausible without a number.", "2023-06-01T12:00:00Z", "human_verified"],
  ["searchfix-agi-old", "explicit_numeric", "Fixture AGI 2030 point estimate from the older note.", "2020-06-01T12:00:00Z", "human_verified"],
  ["searchfix-rejected", "explicit_numeric", "REJECTED_SECRET_PHRASE AGI 2030 must stay hidden.", "2024-01-01T12:00:00Z", "rejected"],
  ["searchfix-unreviewed", "explicit_qualitative", "UNREVIEWED_CANONICAL_PHRASE stays off public search.", "2024-02-01T12:00:00Z", "unreviewed"],
] as const;

export async function seedSearchFixture(pool: pg.Pool): Promise<void> {
  await clearSearchFixture(pool);
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await client.query(
      `INSERT INTO organizations (id, slug, name, organization_type)
       VALUES ($1, 'searchfix-org', 'AGI 2030 Observatory', 'research_lab')`,
      [org],
    );
    await client.query(
      `INSERT INTO people (id, slug, display_name, given_name, family_name, bio_short, inclusion_reason, status)
       VALUES
         ($1, 'searchfix-other', 'Search Fixture Other', 'Search', 'Other', 'Search fixture person with no statements.', 'Search ranking fixture.', 'active'),
         ($2, 'searchfix-speaker', 'Search Fixture Speaker', 'Search', 'Speaker', 'Search fixture person with several statements.', 'Search ranking fixture.', 'active')`,
      [other, speaker],
    );
    await client.query(
      `INSERT INTO topics (id, slug, name, definition, version)
       VALUES ($1, 'searchfix-agi-2030', 'AGI 2030', 'Fixture topic for a dated AGI question. Not a field consensus.', '1')`,
      [topic],
    );
    await client.query(
      `INSERT INTO sources (id, slug, source_type, name, canonical_url, collection_method, owner_person_id, review_state)
       VALUES ($1, 'searchfix-source', 'blog', 'AGI 2030 notes', 'https://synthetic.pdoom.example/searchfix/source', 'fixture', $2, 'human_verified')`,
      [source, speaker],
    );
    await client.query(
      `INSERT INTO source_items (
         id, slug, source_id, logical_key, canonical_url, title, published_at, observed_at, content_hash, content_version, collection_status, availability
       ) VALUES (
         $1, 'searchfix-item', $2, 'searchfix-item', 'https://synthetic.pdoom.example/searchfix/item',
         'AGI 2030 briefing', '2024-06-01T12:00:00Z', '2024-06-01T12:00:00Z', $3, 1, 'collected', 'available'
       )`,
      [item, source, sha256("searchfix-item")],
    );
    await client.query(
      `INSERT INTO affiliations (
         id, person_id, organization_id, role, start_date, confidence_level, verification_detail, review_state
       ) VALUES
         ($1, $2, $3, 'Searchfix private role', '2020-01-01', 'high', 'PRIVATE_REVIEW_NOTE_9f3a', 'human_verified'),
         ($4, $2, $3, 'REJECTED_ROLE_SECRET', '2021-01-01', 'low', 'SHOULD_NOT_LEAK_NOTE', 'rejected')`,
      [affiliation, speaker, org, rejectedAffiliation],
    );
    await client.query(`UPDATE people SET current_affiliation_id = $1 WHERE id = $2`, [affiliation, speaker]);
    for (const [index, row] of statements.entries()) {
      const [slug, statementType, text, eventTime, review] = row;
      const evidence = stableId(`evidence:${slug}`);
      const statement = stableId(`statement:${slug}`);
      await client.query(
        `INSERT INTO evidence_segments (id, slug, source_item_id, segment_kind, sequence, text, segment_hash)
         VALUES ($1, $2, $3, 'text', $4, $5, $6)`,
        [evidence, `${slug}-evidence`, item, index + 1, "Search fixture excerpt.", sha256(slug)],
      );
      await client.query(
        `INSERT INTO statements (
           id, slug, person_id, source_item_id, statement_type, normalized_text, event_time,
           evidence_segment_id, extractor_name, extractor_version, confidence, review_state
         ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'search-fixture', 'search-fixture', 0.5, $9)`,
        [statement, slug, speaker, item, statementType, text, eventTime, evidence, review],
      );
      if (slug.startsWith("searchfix-agi-") && review !== "rejected") {
        await client.query(
          `INSERT INTO statement_topics (statement_id, topic_id, confidence, method) VALUES ($1, $2, 1, 'search-fixture')`,
          [statement, topic],
        );
      }
      if (statementType === "explicit_numeric" && review !== "rejected") {
        await client.query(
          `INSERT INTO forecasts (
             id, statement_id, forecast_kind, question_key, question_text, value_type, value_numeric, unit, horizon_text, review_state
           ) VALUES ($1, $2, 'probability', 'searchfix_agi_2030', 'Fixture probability of AGI by 2030.', 'point', 0.2, 'probability', 'by 2030', 'human_verified')`,
          [stableId(`forecast:${slug}`), statement],
        );
      }
    }
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function clearSearchFixture(pool: pg.Pool): Promise<void> {
  await pool.query(`
    DELETE FROM forecasts WHERE statement_id IN (SELECT id FROM statements WHERE slug LIKE 'searchfix-%');
    DELETE FROM statement_topics WHERE statement_id IN (SELECT id FROM statements WHERE slug LIKE 'searchfix-%');
    DELETE FROM statements WHERE slug LIKE 'searchfix-%';
    DELETE FROM evidence_segments WHERE slug LIKE 'searchfix-%';
    UPDATE people SET current_affiliation_id = NULL WHERE slug LIKE 'searchfix-%';
    DELETE FROM affiliations WHERE role IN ('Searchfix private role', 'REJECTED_ROLE_SECRET');
    DELETE FROM source_items WHERE slug = 'searchfix-item';
    DELETE FROM sources WHERE slug = 'searchfix-source';
    DELETE FROM topics WHERE slug = 'searchfix-agi-2030';
    DELETE FROM people WHERE slug LIKE 'searchfix-%';
    DELETE FROM organizations WHERE slug = 'searchfix-org';
  `);
}

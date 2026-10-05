import { readFileSync } from "node:fs";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { stableId } from "../packages/db/src/ids";
import { createPool } from "../packages/db/src/pool";
import { searchPublic } from "../packages/db/src/search";

const pool = createPool(process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test");
const document = JSON.parse(readFileSync("data/collections/cohort-v2026-09/canonical-live.json", "utf8")) as {
  people: Array<{
    slug: string;
    display_name: string;
    given_name: string | null;
    family_name: string | null;
    bio_short: string;
    inclusion_reason: string;
    cohort_tags: string[];
    status: string;
  }>;
  organizations: Array<{ slug: string; name: string; organization_type: string }>;
};

function hasMark(value: string): boolean {
  return /[^\u0000-\u007F]/.test(value) || /[A-Za-z]-[A-Za-z]/.test(value);
}

const people = document.people.filter((person) =>
  hasMark(person.display_name) || hasMark(person.given_name ?? "") || hasMark(person.family_name ?? ""),
);
const organizations = document.organizations.filter((organization) => hasMark(organization.name));

const insertedPeople: string[] = [];
const insertedOrganizations: string[] = [];

async function searchSlugs(q: string, type: "person" | "organization"): Promise<string[]> {
  const result = await searchPublic({ q, type, mode: "page", limit: 8 }, pool);
  return result.groups[type].data.map((hit) => hit.slug);
}

beforeAll(async () => {
  for (const person of people) {
    const existing = await pool.query(`SELECT 1 FROM people WHERE slug = $1`, [person.slug]);
    if (existing.rowCount) continue;
    await pool.query(
      `INSERT INTO people (id, slug, display_name, given_name, family_name, bio_short, inclusion_reason, cohort_tags, status)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
      [
        stableId(`person:${person.slug}`),
        person.slug,
        person.display_name,
        person.given_name,
        person.family_name,
        person.bio_short,
        person.inclusion_reason,
        person.cohort_tags,
        person.status,
      ],
    );
    insertedPeople.push(person.slug);
  }
  for (const organization of organizations) {
    const existing = await pool.query(`SELECT 1 FROM organizations WHERE slug = $1`, [organization.slug]);
    if (existing.rowCount) continue;
    await pool.query(
      `INSERT INTO organizations (id, slug, name, organization_type) VALUES ($1, $2, $3, $4)`,
      [stableId(`organization:${organization.slug}`), organization.slug, organization.name, organization.organization_type],
    );
    insertedOrganizations.push(organization.slug);
  }
});

afterAll(async () => {
  if (insertedPeople.length) await pool.query(`DELETE FROM people WHERE slug = ANY($1::text[])`, [insertedPeople]);
  if (insertedOrganizations.length) {
    await pool.query(`DELETE FROM organizations WHERE slug = ANY($1::text[])`, [insertedOrganizations]);
  }
  await pool.end();
});

describe("published cohort name navigation", () => {
  it("finds accented and hyphenated people by the ascii name and by the record id", async () => {
    expect(people.map((person) => person.slug)).toEqual(expect.arrayContaining([
      "sebastien-bubeck",
      "lukasz-kaiser",
      "chris-re",
      "tieyan-liu",
      "francois-chollet",
    ]));
    for (const person of people) {
      const typed = [person.given_name, person.family_name].filter(Boolean).join(" ");
      const byName = await searchSlugs(typed, "person");
      expect(byName, typed).toContain(person.slug);
      const byRecord = await searchSlugs(person.slug.replaceAll("-", " "), "person");
      expect(byRecord, person.slug).toContain(person.slug);
    }
  });

  it("finds Tübingen by the ascii spelling and by the ue spelling in the record id", async () => {
    expect(organizations.map((organization) => organization.slug)).toContain("tuebingen");
    expect(await searchSlugs("Tubingen", "organization")).toContain("tuebingen");
    expect(await searchSlugs("Tuebingen", "organization")).toContain("tuebingen");
    expect(await searchSlugs("Tübingen", "organization")).toContain("tuebingen");
  });
});

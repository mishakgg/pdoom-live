"use client";

import { createRequestGate } from "@pdoom/contracts";
import Link from "next/link";
import { useMemo, useState } from "react";

type SearchHit = {
  people: Array<{ slug: string; display_name: string }>;
  statements: Array<{ slug: string; normalized_text: string }>;
  topics: Array<{ slug: string; name: string }>;
};

export function LiveSearch() {
  const gate = useMemo(() => createRequestGate(), []);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit | null>(null);

  async function onChange(value: string) {
    setQ(value);
    const id = gate.next();
    if (value.trim().length < 2) {
      if (gate.shouldApply(id)) setHits(null);
      return;
    }
    const response = await fetch(`/api/search?q=${encodeURIComponent(value.trim())}`);
    if (!gate.shouldApply(id)) return;
    if (!response.ok) {
      setHits(null);
      return;
    }
    setHits((await response.json()) as SearchHit);
  }

  return (
    <form className="search" action="/statements" role="search">
      <label>
        <span className="kicker">Search</span>
        <input
          name="q"
          value={q}
          onChange={(event) => void onChange(event.target.value)}
          placeholder="Person, claim, topic"
          aria-label="Search statements"
        />
      </label>
      {hits ? (
        <ul>
          {hits.people.map((person) => (
            <li key={person.slug}>
              <Link href={`/people/${person.slug}`}>{person.display_name}</Link>
            </li>
          ))}
          {hits.topics.map((topic) => (
            <li key={topic.slug}>
              <Link href={`/topics/${topic.slug}`}>{topic.name}</Link>
            </li>
          ))}
          {hits.statements.slice(0, 4).map((statement) => (
            <li key={statement.slug}>
              <Link href={`/statements/${statement.slug}`}>{statement.normalized_text}</Link>
            </li>
          ))}
        </ul>
      ) : null}
    </form>
  );
}

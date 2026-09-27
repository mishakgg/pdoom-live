"use client";

import { createRequestGate } from "@pdoom/contracts";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type SearchHit = {
  people: Array<{ slug: string; display_name: string }>;
  statements: Array<{ slug: string; normalized_text: string }>;
  topics: Array<{ slug: string; name: string }>;
};

export function LiveSearch() {
  const gate = useMemo(() => createRequestGate(), []);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit | null>(null);
  const [note, setNote] = useState("");
  const expanded = q.trim().length >= 2;

  useEffect(() => {
    const trimmed = q.trim();
    if (trimmed.length < 2) return;
    const controller = new AbortController();
    const id = gate.next();
    const timer = setTimeout(() => {
      void (async () => {
        try {
          const response = await fetch(`/api/search?q=${encodeURIComponent(trimmed)}`, { signal: controller.signal });
          if (!gate.shouldApply(id)) return;
          if (!response.ok) {
            setHits(null);
            setNote("Search could not be completed.");
            return;
          }
          const body = (await response.json()) as SearchHit;
          if (!gate.shouldApply(id)) return;
          const count = body.people.length + body.topics.length + body.statements.length;
          setHits(count ? body : { people: [], statements: [], topics: [] });
          setNote(count ? `${count} matching records.` : "No people, topics, or statements match.");
        } catch (error) {
          if (error instanceof DOMException && error.name === "AbortError") return;
          if (!gate.shouldApply(id)) return;
          setHits(null);
          setNote("Search could not be completed.");
        }
      })();
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [q, gate]);

  return (
    <form className="search" action="/statements" role="search">
      <label htmlFor="site-search">Search the dataset</label>
      <input
        id="site-search"
        type="search"
        name="q"
        value={q}
        enterKeyHint="search"
        autoComplete="off"
        onChange={(event) => {
          const value = event.target.value;
          setQ(value);
          if (value.trim().length < 2) {
            setHits(null);
            setNote("");
          } else {
            setNote("Searching.");
          }
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setQ("");
            setHits(null);
            setNote("");
          }
        }}
        placeholder="Person, claim, or topic"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={expanded}
        aria-controls={expanded ? "site-search-results" : undefined}
      />
      <button className="sr-only" type="submit">Search statements</button>
      {expanded ? (
        <div id="site-search-results" className="search-results">
          <p className="sr-only" role="status">{note || "Searching."}</p>
          {hits && hits.people.length ? (
            <>
              <p className="kicker" id="search-people">People</p>
              <ul aria-labelledby="search-people">
                {hits.people.map((person) => (
                  <li key={person.slug}>
                    <Link href={`/people/${person.slug}`}>{person.display_name}</Link>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {hits && hits.topics.length ? (
            <>
              <p className="kicker" id="search-topics">Topics</p>
              <ul aria-labelledby="search-topics">
                {hits.topics.map((topic) => (
                  <li key={topic.slug}>
                    <Link href={`/topics/${topic.slug}`}>{topic.name}</Link>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {hits && hits.statements.length ? (
            <>
              <p className="kicker" id="search-statements">Statements</p>
              <ul aria-labelledby="search-statements">
                {hits.statements.slice(0, 4).map((statement) => (
                  <li key={statement.slug}>
                    <Link href={`/statements/${statement.slug}`}>{statement.normalized_text}</Link>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {hits && hits.people.length + hits.topics.length + hits.statements.length === 0 ? (
            <p className="meta">No people, topics, or statements match.</p>
          ) : null}
        </div>
      ) : null}
    </form>
  );
}

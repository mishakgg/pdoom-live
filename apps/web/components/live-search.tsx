"use client";

import {
  SEARCH_DEBOUNCE_MS,
  SEARCH_SUGGEST_MIN,
  createRequestGate,
  type SearchResponse,
} from "@pdoom/contracts";
import Link from "next/link";
import { useEffect, useId, useMemo, useState, type KeyboardEvent } from "react";

type Suggestion = { id: string; href: string; label: string; detail?: string; kind: string };

function clipLabel(text: string): string {
  const flat = text.replace(/\s+/g, " ").trim();
  if (flat.length <= 140) return flat;
  return `${flat.slice(0, 139).trimEnd()}…`;
}

function personDetail(person: SearchResponse["groups"]["person"]["data"][number], duplicate: boolean): string {
  const affiliation = person.organization
    ? `${person.organization.role ?? "Role not recorded"}, ${person.organization.name}`
    : "No current affiliation recorded";
  return duplicate ? `${affiliation}. Record ${person.slug}` : affiliation;
}

function suggestionsFrom(response: SearchResponse | null): Suggestion[] {
  if (!response || response.query.reason !== "ok") return [];
  const items: Suggestion[] = [];
  const personNames = new Map<string, number>();
  for (const person of response.groups.person.data) {
    personNames.set(person.display_name, (personNames.get(person.display_name) ?? 0) + 1);
  }
  for (const person of response.groups.person.data) {
    const duplicate = (personNames.get(person.display_name) ?? 0) > 1;
    items.push({
      id: `suggest-person-${person.slug}`,
      href: `/people/${person.slug}`,
      label: person.display_name,
      detail: personDetail(person, duplicate),
      kind: "Person",
    });
  }
  for (const topic of response.groups.topic.data) {
    items.push({ id: `suggest-topic-${topic.slug}`, href: `/topics/${topic.slug}`, label: topic.name, kind: "Topic" });
  }
  for (const statement of response.groups.statement.data) {
    items.push({
      id: `suggest-statement-${statement.slug}`,
      href: `/statements/${statement.slug}`,
      label: clipLabel(statement.normalized_text),
      kind: "Statement",
    });
  }
  for (const organization of response.groups.organization.data) {
    items.push({
      id: `suggest-organization-${organization.slug}`,
      href: `/people?organization=${organization.slug}`,
      label: organization.name,
      kind: "Organization",
    });
  }
  for (const source of response.groups.source.data) {
    items.push({ id: `suggest-source-${source.slug}`, href: `/sources/${source.slug}`, label: source.name, kind: "Source" });
  }
  for (const item of response.groups.source_item.data) {
    items.push({
      id: `suggest-item-${item.slug}`,
      href: `/source-items/${item.slug}`,
      label: item.title ?? "Untitled source item",
      kind: "Source item",
    });
  }
  return items;
}

export function LiveSearch() {
  const gate = useMemo(() => createRequestGate(), []);
  const listId = useId();
  const [q, setQ] = useState("");
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const items = suggestionsFrom(open ? response : null);
  const showList = open && items.length > 0;
  const activeItem = active >= 0 ? items[active] : undefined;

  useEffect(() => {
    const trimmed = q.trim();
    if (trimmed.length < SEARCH_SUGGEST_MIN) return;
    const controller = new AbortController();
    const requestId = gate.next();
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const result = await fetch(`/api/search?q=${encodeURIComponent(trimmed)}&mode=suggest`, {
            signal: controller.signal,
          });
          if (!gate.shouldApply(requestId)) return;
          if (!result.ok) {
            setResponse(null);
            setOpen(false);
            return;
          }
          const body = (await result.json()) as SearchResponse;
          if (!gate.shouldApply(requestId)) return;
          setResponse(body);
          setOpen(true);
          setActive(-1);
        } catch (error) {
          if (error instanceof DOMException && error.name === "AbortError") return;
          if (!gate.shouldApply(requestId)) return;
          setResponse(null);
          setOpen(false);
        }
      })();
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [q, gate]);

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      setActive(-1);
      return;
    }
    if (!showList) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((current) => Math.min(items.length - 1, current + 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((current) => Math.max(-1, current - 1));
    } else if (event.key === "Enter" && activeItem) {
      event.preventDefault();
      document.getElementById(activeItem.id)?.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    }
  }

  const countLabel = items.length === 1 ? "1 search suggestion" : `${items.length} search suggestions`;

  return (
    <form className="search" action="/search" method="get" role="search">
      <label>
        <span className="sr-only">Search</span>
        <input
          name="q"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={showList && activeItem ? activeItem.id : undefined}
          aria-label="Search people, statements, topics, and sources"
          value={q}
          autoComplete="off"
          placeholder="Person, statement, topic, source"
          onChange={(event) => {
            const next = event.target.value;
            setQ(next);
            setResponse(null);
            setOpen(false);
            setActive(-1);
          }}
          onKeyDown={onKeyDown}
        />
      </label>
      <p className="sr-only" role="status" aria-live="polite">
        {q.trim().length < SEARCH_SUGGEST_MIN ? "" : open ? countLabel : ""}
      </p>
      {showList ? (
        <ul id={listId} role="listbox" aria-label="Search suggestions" onMouseDown={(event) => event.preventDefault()}>
          {items.map((item, index) => (
            <li key={item.id} role="presentation">
              <Link id={item.id} role="option" aria-selected={index === active} href={item.href}>
                <span className="kicker">{item.kind}</span>
                <span>{item.label}</span>
                {item.detail ? <span className="meta">{item.detail}</span> : null}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </form>
  );
}

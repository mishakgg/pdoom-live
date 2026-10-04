"use client";

import {
  SEARCH_DEBOUNCE_MS,
  SEARCH_SUGGEST_MIN,
  createRequestGate,
  type SearchResponse,
} from "@pdoom/contracts";
import { useEffect, useId, useMemo, useState, type KeyboardEvent, type MouseEvent } from "react";
import { optionsFromSearch, type EntityKind, type EntityOption } from "@/lib/entity-options";

export type EntitySelection = {
  slug: string;
  name: string;
  detail: string;
};

export function EntitySelect({
  kind,
  label,
  name,
  selected,
}: {
  kind: EntityKind;
  label: string;
  name: string;
  selected: EntitySelection | null;
}) {
  const gate = useMemo(() => createRequestGate(), []);
  const listId = useId();
  const inputId = useId();
  const statusId = useId();
  const [query, setQuery] = useState("");
  const [choice, setChoice] = useState<EntitySelection | null>(selected);
  const [options, setOptions] = useState<EntityOption[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [status, setStatus] = useState("");
  const showList = open && options.length > 0;
  const activeOption = active >= 0 ? options[active] : undefined;

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < SEARCH_SUGGEST_MIN) return;
    const controller = new AbortController();
    const requestId = gate.next();
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const result = await fetch(
            `/api/search?q=${encodeURIComponent(trimmed)}&type=${kind}&mode=page&limit=8`,
            { signal: controller.signal },
          );
          if (!gate.shouldApply(requestId)) return;
          if (!result.ok) {
            setOptions([]);
            setOpen(false);
            setStatus("Suggestions unavailable");
            return;
          }
          const body = (await result.json()) as SearchResponse;
          if (!gate.shouldApply(requestId)) return;
          const next = optionsFromSearch(kind, body);
          setOptions(next);
          setOpen(true);
          setActive(-1);
          setStatus(next.length === 1 ? `1 ${label.toLowerCase()} suggestion` : `${next.length} ${label.toLowerCase()} suggestions`);
        } catch (error) {
          if (error instanceof DOMException && error.name === "AbortError") return;
          if (!gate.shouldApply(requestId)) return;
          setOptions([]);
          setOpen(false);
          setStatus("Suggestions unavailable");
        }
      })();
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, gate, kind, label]);

  function choose(option: EntityOption) {
    setChoice({ slug: option.slug, name: option.name, detail: option.detail });
    setQuery("");
    setOptions([]);
    setOpen(false);
    setActive(-1);
    setStatus(`Selected ${option.accessible}`);
  }

  function clear(event: MouseEvent<HTMLButtonElement>) {
    const form = event.currentTarget.form;
    setChoice(null);
    setStatus(`Cleared ${label.toLowerCase()}`);
    if (!form) return;
    const hidden = form.elements.namedItem(name);
    if (hidden instanceof HTMLInputElement) {
      hidden.value = "";
      hidden.disabled = true;
    }
    form.requestSubmit();
  }

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
      setActive((current) => Math.min(options.length - 1, current + 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((current) => Math.max(-1, current - 1));
    } else if (event.key === "Enter" && activeOption) {
      event.preventDefault();
      choose(activeOption);
    }
  }

  return (
    <div className="entity">
      <label htmlFor={inputId}>{label}</label>
      <input
        id={inputId}
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={showList && activeOption ? `${listId}-${activeOption.slug}` : undefined}
        aria-describedby={statusId}
        value={query}
        autoComplete="off"
        placeholder={choice ? `Change ${label.toLowerCase()}` : "Search by name"}
        onChange={(event) => {
          const next = event.target.value;
          setQuery(next);
          setActive(-1);
          if (next.trim().length < SEARCH_SUGGEST_MIN) {
            setOptions([]);
            setOpen(false);
            setStatus("");
          }
        }}
        onKeyDown={onKeyDown}
      />
      {choice ? (
        <p className="entity-selected">
          <span>
            <strong>{choice.name}</strong>
            <span className="meta"> {choice.detail}</span>
          </span>
          <button type="button" className="secondary" onClick={clear}>Remove {label}</button>
        </p>
      ) : null}
      {choice ? <input type="hidden" name={name} value={choice.slug} /> : null}
      <p id={statusId} className="sr-only" role="status" aria-live="polite">{status}</p>
      {showList ? (
        <ul id={listId} className="suggest" role="listbox" aria-label={`${label} suggestions`} onMouseDown={(event) => event.preventDefault()}>
          {options.map((option, index) => (
            <li key={option.slug} role="presentation">
              <button
                id={`${listId}-${option.slug}`}
                type="button"
                role="option"
                aria-selected={index === active}
                onClick={() => choose(option)}
              >
                <span className="kicker">{label}</span>
                <span>{option.name}</span>
                <span className="meta">{option.detail}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

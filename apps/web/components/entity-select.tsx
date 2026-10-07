"use client";

import {
  SEARCH_DEBOUNCE_MS,
  SEARCH_SUGGEST_MIN,
  createRequestGate,
  type SearchResponse,
} from "@pdoom/contracts/browser";
import { useCallback, useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent } from "react";
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
  const root = useRef<HTMLDivElement>(null);
  const pending = useRef<AbortController | null>(null);
  const [requestEpoch, setRequestEpoch] = useState(0);
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
  const activeId = activeOption ? `${listId}-${activeOption.slug}` : undefined;

  const dismiss = useCallback(() => {
    gate.next();
    pending.current?.abort();
    setOpen(false);
    setActive(-1);
    setStatus("");
  }, [gate]);

  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      if (event.target instanceof Node && !root.current?.contains(event.target)) dismiss();
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [dismiss]);

  useEffect(() => {
    if (activeId) document.getElementById(activeId)?.scrollIntoView?.({ block: "nearest" });
  }, [activeId]);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < SEARCH_SUGGEST_MIN) return;
    const controller = new AbortController();
    pending.current = controller;
    const requestId = gate.next();
    const timer = window.setTimeout(() => {
      if (!gate.shouldApply(requestId)) return;
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
      gate.next();
    };
  }, [query, gate, kind, label, requestEpoch]);

  function choose(option: EntityOption) {
    dismiss();
    setChoice({ slug: option.slug, name: option.name, detail: option.detail });
    setQuery("");
    setOptions([]);
    setOpen(false);
    setActive(-1);
    setStatus(`Selected ${option.accessible}`);
  }

  function clear(event: MouseEvent<HTMLButtonElement>) {
    const form = event.currentTarget.form;
    dismiss();
    setQuery("");
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
      dismiss();
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
    <div
      ref={root}
      className="entity"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) dismiss();
      }}
    >
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
        onFocus={() => setRequestEpoch((epoch) => epoch + 1)}
        onChange={(event) => {
          dismiss();
          const next = event.target.value;
          setQuery(next);
          setOptions([]);
          setOpen(false);
          setActive(-1);
          setStatus(next.trim().length < SEARCH_SUGGEST_MIN ? "" : "Searching");
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

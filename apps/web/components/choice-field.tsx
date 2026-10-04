"use client";

import { useMemo, useState } from "react";

export type ChoiceOption = {
  value: string;
  label: string;
  hint?: string;
};

export function ChoiceField({
  name,
  label,
  hint,
  options,
  defaultValue = "",
  emptyLabel,
}: {
  name: string;
  label: string;
  hint?: string;
  options: ChoiceOption[];
  defaultValue?: string;
  emptyLabel: string;
}) {
  const [query, setQuery] = useState("");
  const [value, setValue] = useState(defaultValue);
  const selected = options.find((option) => option.value === value);
  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return options;
    return options.filter((option) => {
      if (option.value === value) return true;
      return `${option.label} ${option.value} ${option.hint ?? ""}`.toLowerCase().includes(needle);
    });
  }, [options, query, value]);

  return (
    <div className="choice">
      <label>
        {label}
        <input
          type="search"
          value={query}
          placeholder="Type to filter"
          aria-label={`Filter ${label}`}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      <select name={name} value={value} onChange={(event) => setValue(event.target.value)} aria-label={label}>
        <option value="">{emptyLabel}</option>
        {shown.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
      <p className="meta">{selected?.hint ?? hint ?? "Choose a value, or leave the field unchanged."}</p>
    </div>
  );
}

export function ReferenceList({
  items,
}: {
  items: Array<{ key: string; label: string; note: string; suggested: boolean }>;
}) {
  const [query, setQuery] = useState("");
  const needle = query.trim().toLowerCase();
  const shown = items.filter((item) => {
    if (!needle) return true;
    return `${item.label} ${item.key} ${item.note}`.toLowerCase().includes(needle);
  });
  return (
    <details className="technical">
      <summary>Question reference</summary>
      <label>
        Filter the reference
        <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} />
      </label>
      <ul className="reference-list">
        {shown.map((item) => (
          <li key={item.key}>
            <strong>{item.label}</strong>
            <code>{item.key}</code>
            <span>{item.note}</span>
            {item.suggested ? <span> Suggested from the text; still confirm it.</span> : null}
          </li>
        ))}
        {shown.length === 0 ? <li>No question matches that filter.</li> : null}
      </ul>
    </details>
  );
}

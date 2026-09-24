import { STATEMENT_TYPE_LABELS, type StatementType } from "@pdoom/contracts";

export function typeLabel(type: string): string {
  if (type in STATEMENT_TYPE_LABELS) return STATEMENT_TYPE_LABELS[type as StatementType];
  return type;
}

export function formatWhen(value: string | null | undefined): string {
  if (!value) return "Time unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Time unknown";
  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    hourCycle: "h23",
  }).format(date) + " UTC";
}

export function formatDay(value: string | null | undefined): string {
  if (!value) return "Date unknown";
  return formatWhen(value).replace(/,?\s+\d{2}:\d{2} UTC$/, " UTC").replace(" UTC", "");
}

export function formatProbability(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const pct = Math.round(value * 1000) / 10;
  return Number.isInteger(pct) ? `${pct.toFixed(0)}%` : `${pct.toFixed(1)}%`;
}

export function formatValue(input: {
  value_type?: string | null;
  value_numeric?: number | null;
  value_min?: number | null;
  value_max?: number | null;
  unit?: string | null;
}): string {
  if (!input.value_type || input.value_type === "none") return "No numeric value";
  if (input.unit === "probability") {
    if (input.value_type === "range") {
      return `${formatProbability(input.value_min)}–${formatProbability(input.value_max)}`;
    }
    return formatProbability(input.value_numeric);
  }
  if (input.value_type === "range") return `${input.value_min}–${input.value_max} ${input.unit ?? ""}`.trim();
  return `${input.value_numeric} ${input.unit ?? ""}`.trim();
}

export function reviewLabel(state: string): string {
  return state.replaceAll("_", " ");
}

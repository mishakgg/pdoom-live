import { STATEMENT_TYPE_LABELS, type StatementType } from "@pdoom/contracts/browser";

const REVIEW_LABELS: Record<string, string> = {
  human_verified: "Human verified",
  machine_validated: "Machine validated",
  needs_review: "Needs review",
  unreviewed: "Unreviewed",
  rejected: "Rejected",
};

export function phraseLabel(value: string): string {
  const text = value.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function typeLabel(type: string): string {
  if (type in STATEMENT_TYPE_LABELS) return STATEMENT_TYPE_LABELS[type as StatementType];
  return phraseLabel(type);
}

export function reviewLabel(state: string): string {
  return REVIEW_LABELS[state] ?? phraseLabel(state);
}

export function isHumanVerified(state: string | null | undefined): boolean {
  return state === "human_verified";
}

export function countLabel(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

let utcDateTimeFormatter: Intl.DateTimeFormat | undefined;

export function formatWhen(value: string | null | undefined): string {
  if (!value) return "Time unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Time unknown";
  // One lazy formatter avoids repeated locale setup in long server-rendered lists.
  utcDateTimeFormatter ??= new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    hourCycle: "h23",
  });
  return utcDateTimeFormatter.format(date) + " UTC";
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

export function formatYear(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  if (Number.isInteger(value)) return String(value);
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

export function formatQuantity(value: number | null | undefined, unit: string | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  if (unit === "probability") return formatProbability(value);
  if (unit === "share") return `${formatProbability(value)} share`;
  if (unit === "year") return formatYear(value);
  if (unit === "percentage_points") {
    const rounded = Math.round(value * 10) / 10;
    const text = Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1);
    return `${text} percentage points`;
  }
  const rounded = Math.round(value * 1000) / 1000;
  return `${rounded} ${unit ?? ""}`.trim();
}

export function formatEstimate(input: {
  value_type?: string | null;
  value_numeric?: number | null;
  value_min?: number | null;
  value_max?: number | null;
  unit?: string | null;
}): string {
  if (input.value_type === "range") {
    return `${formatQuantity(input.value_min, input.unit)}–${formatQuantity(input.value_max, input.unit)}`;
  }
  return formatQuantity(input.value_numeric, input.unit);
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

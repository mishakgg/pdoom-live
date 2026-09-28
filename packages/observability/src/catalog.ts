import raw from "../catalog.json";

export const catalog = raw;

export type Guardrails = typeof catalog.guardrails;

export const metricNames = new Set(catalog.metrics.map((metric) => metric.name));

const labelSets = new Map<string, Set<string>>(
  Object.entries(catalog.labels).map(([name, values]) => [name, new Set(values)]),
);

export function allowedLabel(group: string, value: string | null | undefined, fallback: string): string {
  const allowed = labelSets.get(group);
  if (value && allowed?.has(value)) return value;
  if (allowed?.has(fallback)) return fallback;
  return "other";
}

export function assertKnownMetric(name: string): void {
  if (!metricNames.has(name)) throw new Error(`unknown metric ${name}`);
}

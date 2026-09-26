const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export function normalizePrefixedId(value: string, prefix: "person" | "org"): string {
  const trimmed = value.trim();
  const marker = `${prefix}:`;
  if (!trimmed.startsWith(marker)) {
    throw new Error(`malformed ${prefix} id: ${value}`);
  }
  const slug = trimmed.slice(marker.length);
  if (!SLUG.test(slug) || slug.length > 80) {
    throw new Error(`malformed ${prefix} id: ${value}`);
  }
  return slug;
}

export function assertNormalizedSlug(value: string, prefix: "person" | "org", slug: string): void {
  const normalized = normalizePrefixedId(value, prefix);
  if (normalized !== slug) {
    throw new Error(`${prefix} id ${value} does not match slug ${slug}`);
  }
}

const ISO_TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;

export function normalizeTimestamp(value: string): string {
  if (!ISO_TIMESTAMP.test(value)) {
    throw new Error(`invalid timestamp: ${value}`);
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new Error(`invalid timestamp: ${value}`);
  }
  return date.toISOString();
}

export function timestampsMatch(left: string, right: string): boolean {
  return normalizeTimestamp(left) === normalizeTimestamp(right);
}

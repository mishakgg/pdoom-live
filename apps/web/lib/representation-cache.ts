import { publicContentRevision, withConsistentRead } from "@pdoom/db";
import type pg from "pg";
import type { PublicRepresentation } from "./public-http";
import { singleFlight } from "./single-flight";

const TTL_MS = 60_000;
const MAX_ENTRIES = 48;
const MAX_BODY_BYTES = 256 * 1024;
const MAX_TOTAL_BYTES = 2 * 1024 * 1024;

type Entry = PublicRepresentation & {
  revision: string;
  storedAt: number;
  bytes: number;
};

const entries = new Map<string, Entry>();
let totalBytes = 0;
let revisionFlight: Promise<string> | null = null;

const counters = {
  heavy: 0,
  reused: 0,
  revisionReads: 0,
};

export function publicOriginCounters() {
  return { ...counters };
}

export function resetPublicRepresentationCache(): void {
  entries.clear();
  totalBytes = 0;
  revisionFlight = null;
  counters.heavy = 0;
  counters.reused = 0;
  counters.revisionReads = 0;
}

export function representationKey(url: URL): string {
  const path = url.pathname.replace(/\/+$/, "") || "/";
  const params = [...url.searchParams.entries()].sort((left, right) => {
    if (left[0] === right[0]) return left[1] < right[1] ? -1 : left[1] > right[1] ? 1 : 0;
    return left[0] < right[0] ? -1 : 1;
  });
  return `${path}?${params.map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`).join("&")}`;
}

function remember(key: string, revision: string, representation: PublicRepresentation): void {
  if (key.length > 2048) return;
  const bytes = Buffer.byteLength(representation.body);
  if (bytes > MAX_BODY_BYTES) return;
  const previous = entries.get(key);
  if (previous) {
    entries.delete(key);
    totalBytes -= previous.bytes;
  }
  while ((entries.size >= MAX_ENTRIES || totalBytes + bytes > MAX_TOTAL_BYTES) && entries.size > 0) {
    const oldest = entries.keys().next().value as string | undefined;
    if (!oldest) break;
    const removed = entries.get(oldest);
    entries.delete(oldest);
    totalBytes -= removed?.bytes ?? 0;
  }
  if (totalBytes + bytes > MAX_TOTAL_BYTES) return;
  entries.set(key, { ...representation, revision, storedAt: Date.now(), bytes });
  totalBytes += bytes;
}

function lookup(key: string, revision: string): PublicRepresentation | null {
  const entry = entries.get(key);
  if (!entry) return null;
  if (entry.revision !== revision || Date.now() - entry.storedAt > TTL_MS) {
    entries.delete(key);
    totalBytes -= entry.bytes;
    return null;
  }
  entries.delete(key);
  entries.set(key, entry);
  return { body: entry.body, etag: entry.etag, headers: entry.headers };
}

function sharedPublicRevision(db: pg.Pool): Promise<string> {
  if (!revisionFlight) {
    revisionFlight = publicContentRevision(db)
      .then((revision) => {
        counters.revisionReads += 1;
        return revision;
      })
      .finally(() => {
        revisionFlight = null;
      });
  }
  return revisionFlight;
}

/**
 * Repeat a public GET without rebuilding it when the content revision is
 * unchanged. A miss reads the revision again inside the same snapshot as the
 * payload so the cached bytes match that revision. Failures are not cached.
 */
export async function loadPublicRepresentation(
  key: string,
  db: pg.Pool,
  produce: (db: pg.PoolClient) => Promise<PublicRepresentation | null>,
): Promise<PublicRepresentation | null> {
  return singleFlight(`public:${key}`, async () => {
    const revision = await sharedPublicRevision(db);
    const cached = lookup(key, revision);
    if (cached) {
      counters.reused += 1;
      return cached;
    }
    return withConsistentRead(db, async (client) => {
      const freshRevision = await publicContentRevision(client);
      counters.revisionReads += 1;
      const again = lookup(key, freshRevision);
      if (again) {
        counters.reused += 1;
        return again;
      }
      const produced = await produce(client);
      counters.heavy += 1;
      if (produced) remember(key, freshRevision, produced);
      return produced;
    });
  });
}

/** Drops stale responses when a newer request has already started. */
export function createRequestGate() {
  let latest = 0;
  return {
    next(): number {
      latest += 1;
      return latest;
    },
    shouldApply(id: number): boolean {
      return id === latest;
    },
  };
}

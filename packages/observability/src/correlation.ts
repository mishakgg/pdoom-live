import { AsyncLocalStorage } from "node:async_hooks";
import { randomUUID } from "node:crypto";

const ID = /^[A-Za-z0-9_-]{8,64}$/;

export type CorrelationContext = {
  requestId?: string;
  runId?: string;
};

const storage = new AsyncLocalStorage<CorrelationContext>();

export function createCorrelationId(): string {
  return randomUUID().replace(/-/g, "");
}

export function acceptCorrelationId(value: string | null | undefined): string {
  if (value && ID.test(value)) return value;
  return createCorrelationId();
}

export function runWithCorrelation<T>(context: CorrelationContext, fn: () => T): T {
  const current = storage.getStore() ?? {};
  return storage.run({ ...current, ...context }, fn);
}

export function currentCorrelation(): CorrelationContext {
  return storage.getStore() ?? {};
}

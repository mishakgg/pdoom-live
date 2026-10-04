const flights = new Map<string, Promise<unknown>>();
const MAX_FLIGHTS = 64;

export class FlightLimitError extends Error {
  constructor() {
    super("flight_limit");
    this.name = "FlightLimitError";
  }
}

export function resetFlights(): void {
  flights.clear();
}

/**
 * Share one in-flight promise for a key. A rejection is not remembered:
 * the key is removed before waiters observe the failure, and the next
 * caller starts a new attempt.
 */
export function singleFlight<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const existing = flights.get(key) as Promise<T> | undefined;
  if (existing) return existing;
  if (flights.size >= MAX_FLIGHTS) return Promise.reject(new FlightLimitError());
  const promise = Promise.resolve()
    .then(fn)
    .finally(() => {
      if (flights.get(key) === promise) flights.delete(key);
    });
  flights.set(key, promise);
  return promise;
}

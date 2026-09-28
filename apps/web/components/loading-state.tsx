export function LoadingState() {
  return (
    <div className="loading" role="status" aria-live="polite">
      <p className="kicker">Loading</p>
      <p>Retrieving the public record.</p>
      <div className="loading-block" aria-hidden="true" />
      <div className="loading-block" aria-hidden="true" />
      <div className="loading-block short" aria-hidden="true" />
    </div>
  );
}

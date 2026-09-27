"use client";

export default function DatasetError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <>
      <h1>This page could not be loaded</h1>
      <p className="warning">The dataset is temporarily unavailable. Nothing on this page is a forecast.</p>
      <button type="button" onClick={() => reset()}>Try again</button>
    </>
  );
}

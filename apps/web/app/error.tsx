"use client";

import Link from "next/link";
import { APPLICATION_ERROR_BODY, APPLICATION_ERROR_TITLE } from "@/lib/presentation";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <section className="panel state state-warning" role="alert">
      <p className="kicker">Application error</p>
      <h1>{APPLICATION_ERROR_TITLE}</h1>
      <p>{APPLICATION_ERROR_BODY}</p>
      {error.digest ? <p className="meta">Reference {error.digest}</p> : null}
      <div className="pager">
        <button type="button" onClick={() => reset()}>Try again</button>
        <Link className="button secondary" href="/">Back to activity</Link>
      </div>
    </section>
  );
}

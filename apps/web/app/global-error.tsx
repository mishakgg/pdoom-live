"use client";

import Link from "next/link";
import { APPLICATION_ERROR_BODY, APPLICATION_ERROR_TITLE } from "@/lib/presentation";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: "#f3f6f4", color: "#17211e", fontFamily: "\"Public Sans\", \"Segoe UI\", sans-serif", lineHeight: 1.55 }}>
        <main style={{ maxWidth: "40rem", margin: "0 auto", padding: "2rem 1.25rem" }}>
          <p style={{ letterSpacing: "0.06em", textTransform: "uppercase", fontSize: "0.78rem", fontWeight: 700, color: "#3e4c48" }}>
            Application error
          </p>
          <h1>{APPLICATION_ERROR_TITLE}</h1>
          <p>{APPLICATION_ERROR_BODY}</p>
          {error.digest ? <p>Reference {error.digest}</p> : null}
          <p>
            <button type="button" onClick={() => reset()}>Try again</button>
            {" "}
            <Link href="/">Back to activity</Link>
          </p>
        </main>
      </body>
    </html>
  );
}

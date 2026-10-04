"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useFormStatus } from "react-dom";
import { submitReview } from "@/app/curation/actions";

function SubmitDecision() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending}>
      {pending ? "Saving decision…" : "Record decision"}
    </button>
  );
}

export function ReviewForm({ children }: { children: ReactNode }) {
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!dirty) return;
    function warn(event: BeforeUnloadEvent) {
      event.preventDefault();
    }
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  return (
    <form
      id="decision"
      className="review-form stack"
      action={submitReview}
      onInput={() => setDirty(true)}
    >
      <div className="review-form-head">
        <h2>Decision</h2>
        {dirty ? (
          <p className="unsaved" role="status">Unsaved changes. Nothing is recorded until you submit this decision.</p>
        ) : (
          <p className="meta">No pending edits in this form.</p>
        )}
      </div>
      {children}
      <SubmitDecision />
    </form>
  );
}

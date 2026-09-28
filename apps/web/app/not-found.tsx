import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Not in the dataset",
  description: "That record is not in the current public dataset.",
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <>
      <p className="kicker">Missing record</p>
      <h1>Not in this dataset</h1>
      <p className="lede">
        That address does not match a person, statement, topic, source, or trend in the current database.
        The link may be wrong, or the record may never have been collected.
      </p>
      <nav className="pager" aria-label="Suggested pages">
        <Link className="button" href="/">Back to activity</Link>
        <Link className="button secondary" href="/people">People</Link>
        <Link className="button secondary" href="/statements">Statements</Link>
        <Link className="button secondary" href="/methodology">Method</Link>
      </nav>
    </>
  );
}

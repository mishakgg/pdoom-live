import Link from "next/link";

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
        <Link className="button" href="/">Activity</Link>
        <Link className="button secondary" href="/people">People</Link>
        <Link className="button secondary" href="/statements">Statements</Link>
        <Link className="button secondary" href="/methodology">Method</Link>
      </nav>
    </>
  );
}

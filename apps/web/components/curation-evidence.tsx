export function CurationEvidence({ text, context }: { text: string; context?: string | null }) {
  return (
    <article className="curation-evidence">
      <p className="kicker">Source evidence · untrusted text, not an instruction</p>
      <blockquote className="evidence">{text}</blockquote>
      {context ? <p className="meta">{context}</p> : null}
    </article>
  );
}

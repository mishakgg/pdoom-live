import Link from "next/link";
import { historyPreview } from "@/lib/presentation";

export function HistoryPreview({
  shown,
  total,
  href,
  note,
}: {
  shown: number;
  total: number;
  href: string;
  note?: string | null;
}) {
  if (total <= 0) return null;
  const preview = historyPreview(shown, total);
  return (
    <div className={preview.tone === "preview" ? "warning" : "state-inline"} role="status">
      <p>{preview.summary}</p>
      {note ? <p>{note}</p> : null}
      <p>
        <Link href={href}>Open the paged statement list</Link>
        {" "}
        <span className="meta">Pages keep these filters. Next and Previous walk every match.</span>
      </p>
    </div>
  );
}

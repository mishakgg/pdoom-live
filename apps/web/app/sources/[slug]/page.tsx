import { getSource } from "@pdoom/db";
import { formatWhen } from "@/lib/format";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function SourcePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const source = await getSource(slug);
  if (!source) notFound();
  return (
    <>
      <p className="kicker">{source.source_type} · {source.collection_method}</p>
      <h1>{source.name}</h1>
      <p className="lede">{source.rights_notes}</p>
      {source.items.map((item) => (
        <article className="card" key={item.slug}>
          <h2><Link href={`/source-items/${item.slug}`}>{item.title}</Link></h2>
          <p className="meta">Published {formatWhen(item.published_at)} · observed {formatWhen(item.observed_at)} · {item.collection_status} · {item.availability}</p>
        </article>
      ))}
    </>
  );
}

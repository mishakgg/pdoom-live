import { isIndexableReviewState } from "@pdoom/contracts";
import { JsonLd } from "@/components/json-ld";
import { formatWhen } from "@/lib/format";
import { loadSource } from "@/lib/loaders";
import { canonicalOrigin, notFoundMetadata, pageMetadata, sourceFields } from "@/lib/seo";
import { sourceStructuredData } from "@/lib/structured-data";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const source = await loadSource(slug);
  if (!source) return notFoundMetadata();
  return pageMetadata(
    canonicalOrigin(),
    sourceFields({
      slug: source.slug,
      name: source.name,
      source_type: source.source_type,
      indexable: isIndexableReviewState(source.review_state),
    }),
  );
}

export default async function SourcePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const source = await loadSource(slug);
  if (!source) notFound();
  const indexable = isIndexableReviewState(source.review_state);
  return (
    <>
      {indexable ? (
        <JsonLd
          data={sourceStructuredData({
            origin: canonicalOrigin(),
            slug: source.slug,
            name: source.name,
            source_type: source.source_type,
          })}
        />
      ) : null}
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

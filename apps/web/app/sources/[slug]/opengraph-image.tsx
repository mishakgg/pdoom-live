import { isIndexableReviewState } from "@pdoom/contracts";
import { loadSource } from "@/lib/loaders";
import { ogContentType, ogSize, renderDiscoveryImage } from "@/lib/og-image";
import { listPageFields, sourceFields } from "@/lib/seo";

export const alt = "pdoom.live source";
export const size = ogSize;
export const contentType = ogContentType;
export const dynamic = "force-dynamic";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const source = await loadSource(slug);
  if (!source) return renderDiscoveryImage(listPageFields("home").card);
  return renderDiscoveryImage(
    sourceFields({
      slug: source.slug,
      name: source.name,
      source_type: source.source_type,
      indexable: isIndexableReviewState(source.review_state),
    }).card,
  );
}

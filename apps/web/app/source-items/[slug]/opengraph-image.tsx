import { loadSourceItemDiscovery } from "@/lib/loaders";
import { ogContentType, ogSize, renderDiscoveryImage } from "@/lib/og-image";
import { listPageFields, sourceItemFields } from "@/lib/seo";

export const alt = "pdoom.live source item";
export const size = ogSize;
export const contentType = ogContentType;
export const dynamic = "force-dynamic";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const item = await loadSourceItemDiscovery(slug);
  if (!item) return renderDiscoveryImage(listPageFields("home").card);
  return renderDiscoveryImage(sourceItemFields(item).card);
}

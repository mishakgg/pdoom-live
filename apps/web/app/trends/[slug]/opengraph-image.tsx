import { loadTrend } from "@/lib/loaders";
import { ogContentType, ogSize, renderDiscoveryImage } from "@/lib/og-image";
import { listPageFields, trendFields } from "@/lib/seo";

export const alt = "pdoom.live trend";
export const size = ogSize;
export const contentType = ogContentType;
export const dynamic = "force-dynamic";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const trend = await loadTrend(slug);
  if (!trend) return renderDiscoveryImage(listPageFields("home").card);
  return renderDiscoveryImage(
    trendFields({
      slug: trend.slug,
      name: trend.name,
      method_version: trend.method_version,
      cohort_version: trend.cohort_version,
    }).card,
  );
}

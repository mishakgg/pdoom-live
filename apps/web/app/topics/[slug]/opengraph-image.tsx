import { loadTopic } from "@/lib/loaders";
import { ogContentType, ogSize, renderDiscoveryImage } from "@/lib/og-image";
import { listPageFields, topicFields } from "@/lib/seo";

export const alt = "pdoom.live topic";
export const size = ogSize;
export const contentType = ogContentType;
export const dynamic = "force-dynamic";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const topic = await loadTopic(slug);
  if (!topic) return renderDiscoveryImage(listPageFields("home").card);
  return renderDiscoveryImage(topicFields(topic).card);
}

import { listPageFields } from "@/lib/seo";
import { ogContentType, ogSize, renderDiscoveryImage } from "@/lib/og-image";

export const alt = "pdoom.live";
export const size = ogSize;
export const contentType = ogContentType;
export const dynamic = "force-dynamic";

export default async function Image() {
  return renderDiscoveryImage(listPageFields("home").card);
}

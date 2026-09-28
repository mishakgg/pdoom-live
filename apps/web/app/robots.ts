import type { MetadataRoute } from "next";
import { canonicalOrigin, robotsDocument } from "@/lib/seo";

export const dynamic = "force-dynamic";

export default function robots(): MetadataRoute.Robots {
  return robotsDocument(canonicalOrigin());
}

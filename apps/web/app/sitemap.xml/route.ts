import { countSitemapRecords, getPool, listSitemapRecords } from "@pdoom/db";
import {
  canonicalOrigin,
  renderSitemapIndex,
  renderUrlSet,
  sitemapChunkBounds,
  sitemapChunkPlan,
  toSitemapLinks,
} from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function GET() {
  const origin = canonicalOrigin();
  const pool = getPool();
  const count = await countSitemapRecords(pool);
  const ids = sitemapChunkPlan(count);
  const xml =
    ids.length === 1
      ? renderUrlSet(toSitemapLinks(origin, await listSitemapRecords(pool, sitemapChunkBounds(0)), true))
      : renderSitemapIndex(origin, ids);
  return new Response(xml, {
    headers: {
      "content-type": "application/xml; charset=utf-8",
      "cache-control": "public, max-age=300",
    },
  });
}

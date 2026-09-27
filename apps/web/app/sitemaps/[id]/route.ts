import { countSitemapRecords, getPool, listSitemapRecords } from "@pdoom/db";
import { canonicalOrigin, renderUrlSet, sitemapChunkBounds, sitemapChunkPlan, toSitemapLinks } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const numeric = Number(id.replace(/\.xml$/, ""));
  const pool = getPool();
  const ids = sitemapChunkPlan(await countSitemapRecords(pool));
  if (!Number.isInteger(numeric) || !ids.includes(numeric) || ids.length === 1) {
    return new Response("Unknown sitemap", { status: 404 });
  }
  const origin = canonicalOrigin();
  const records = await listSitemapRecords(pool, sitemapChunkBounds(numeric));
  const xml = renderUrlSet(toSitemapLinks(origin, records, numeric === 0));
  return new Response(xml, {
    headers: {
      "content-type": "application/xml; charset=utf-8",
      "cache-control": "public, max-age=300",
    },
  });
}

import { getPool, listFeedEntries } from "@pdoom/db";
import { FEED_LIMIT, renderAtomFeed } from "@/lib/feed";
import { canonicalOrigin } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const entries = await listFeedEntries(getPool(), FEED_LIMIT);
    const xml = renderAtomFeed(canonicalOrigin(), entries);
    return new Response(xml, {
      headers: {
        "content-type": "application/atom+xml; charset=utf-8",
        "cache-control": "public, max-age=300",
        "x-robots-tag": "noindex",
      },
    });
  } catch (error) {
    console.error("feed failed", error instanceof Error ? error.name : "error");
    return new Response("Feed unavailable", { status: 503, headers: { "x-robots-tag": "noindex" } });
  }
}

import { isIndexablePersonStatus } from "@pdoom/contracts";
import { loadDataset, loadPerson } from "@/lib/loaders";
import { ogContentType, ogSize, renderDiscoveryImage } from "@/lib/og-image";
import { listPageFields, personFields } from "@/lib/seo";

export const alt = "pdoom.live person";
export const size = ogSize;
export const contentType = ogContentType;
export const dynamic = "force-dynamic";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [person, dataset] = await Promise.all([loadPerson(slug), loadDataset()]);
  if (!person) return renderDiscoveryImage(listPageFields("home").card);
  return renderDiscoveryImage(
    personFields({
      slug: person.slug,
      display_name: person.display_name,
      bio_short: person.bio_short,
      status: person.status,
      dataset_kind: dataset?.dataset_kind ?? null,
      indexable: isIndexablePersonStatus(person.status),
    }).card,
  );
}

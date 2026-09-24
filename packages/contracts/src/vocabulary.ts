import mapDocument from "../vocabulary-map.json" with { type: "json" };
import {
  ATTRIBUTION_METHODS,
  COLLECTION_METHODS,
  ORGANIZATION_TYPES,
  SOURCE_TYPES,
  VERIFICATION_METHODS,
} from "./enums";

export const VOCABULARY_MAP = mapDocument;

const CANONICAL = {
  organization_type: ORGANIZATION_TYPES,
  source_type: SOURCE_TYPES,
  collection_method: COLLECTION_METHODS,
  verification_method: VERIFICATION_METHODS,
  attribution_method: ATTRIBUTION_METHODS,
} as const;

export type VocabularyKind = keyof typeof CANONICAL;

export type MappedVocabulary = {
  canonical: string;
  detail: string | null;
};

export function mapVocabulary(kind: VocabularyKind, value: string): MappedVocabulary {
  const table = VOCABULARY_MAP[kind] as Record<string, string>;
  const canonical = table[value];
  if (!canonical || !(CANONICAL[kind] as readonly string[]).includes(canonical)) {
    throw new Error(`unmapped ${kind}: ${value}`);
  }
  return { canonical, detail: canonical === value ? null : value };
}

const PROBABILITY_TEXT =
  /^(?:(?:0|1)(?:\.0+)?|0?\.\d+|(?:100(?:\.0+)?|\d{1,2}(?:\.\d+)?)\s*(?:%|percent))$/i;

/**
 * Parses a standalone explicit probability. Qualitative words and surrounding
 * prose, including instruction-like text, do not yield a number.
 * Percents are returned on the 0–1 scale.
 */
export function parseExplicitProbability(input: string): number | null {
  const trimmed = input.trim();
  if (!PROBABILITY_TEXT.test(trimmed)) return null;
  const percent = /%\s*$|percent$/i.test(trimmed);
  const numeric = Number(trimmed.replace(/%|percent/gi, "").trim());
  if (!Number.isFinite(numeric)) return null;
  const value = percent ? numeric / 100 : numeric;
  if (value < 0 || value > 1) return null;
  return value;
}

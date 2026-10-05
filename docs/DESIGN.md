# Design direction

pdoom.live presents as a research ledger: a quiet instrument for reading sourced beliefs, not a magazine and not a doom gauge.

## Surfaces and type

- The mast is a full-bleed ink bar (`#10201b`) with a cream wordmark and a gold mark for the current page. The page canvas stays a cool mineral gray (`#f3f6f4`). Reading surfaces are white cards with a soft shadow.
- Text is near-black green-ink. Muted text stays dark enough to read as secondary, not decorative.
- Body copy and interior headings use Public Sans at 16px. A long question title stays in Public Sans so it can occupy two lines without pushing the chart below the first desktop screen.
- Newsreader is the wordmark and the homepage title only.
- Monospace is reserved for hashes, stored keys inside technical disclosures, and short identifiers.
- Numbers that are compared — counts, probabilities, years — use tabular figures.

## Accent

Teal marks links and numeric estimates. Gold marks the current page on the dark mast. Amber marks qualitative views and the synthetic-data banner. Slate marks model-inferred signals. Warnings use a rust border. Color is paired with text or shape: probability points are filled circles on a tinted scale, predicted years are squares, ranges are open strokes.

## Composition

- Primary navigation is one compact row on the dark mast: Activity, People, Topics, Statements, Trends, then Sources, Search, Data, and Method. Search in the header is a field, separate from those links. Its visible label is the field itself; the accessible name stays on the combobox.
- The homepage puts the title beside the widest comparison, with the chart in the first screen. Three starting points sit under the title: statements, that comparison, and freshness. Newest statements follow. Dataset clocks sit below that work, still on the page, labeled as a stored reading. The homepage comparison is a preview; the full table, method, and exclusions stay on the question page.
- A statement card carries a left border in the estimate’s class color: teal for an explicit number, amber for a qualitative view, slate for a model-inferred signal.
- Prose stays near a 66-character measure. Charts sit on a tinted plot. Tables use the full column.
- A trend page leads with the question, the exact scope, the sample, and one chart. The panel repeats the question as a heading for the section, collapsed to a one-pixel accessible heading when the page title already states it. Method strings, stored keys, and cohort definitions sit in a disclosure after the evidence.
- Dataset clocks are labeled tiles under the homepage work, with a heading that says they describe the stored reading. The curator count strip stays a single line. The curator queue is an operator table. Record review places the source excerpt beside the interpretation on wide screens, with attribution, duplicates, and the decision form in later sections. On a narrow screen, filter fields sit in two columns and any explanatory note spans the full width.

## Trust language

Synthetic fixtures say “Synthetic demo data” at the top of every page that renders the dataset. A corpus-read time is labeled as a read of stored records. It is not described as live collection. Stored review state, a machine recommendation, and the effective state stay labeled separately. A recommendation is not human verification. Cohort versions are written as “version”, so a slug that already contains a version token is not followed by a bare number.

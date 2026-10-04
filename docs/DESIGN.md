# Design direction

pdoom.live presents as a research ledger: a quiet instrument for reading sourced beliefs, not a magazine and not a doom gauge.

## Surfaces and type

- Canvas is a cool mineral gray (`#f3f6f4`). Cards and the page header sit on white.
- Text is near-black green-ink. Muted text stays dark enough to read as secondary, not decorative.
- Body and headings use Public Sans at 16px with open line spacing. Headings stay modest so a long question can occupy two lines without dominating the viewport.
- Newsreader remains only in the `pdoom` wordmark.
- Monospace is reserved for hashes, stored keys inside technical disclosures, and short identifiers.
- Numbers that are compared — counts, probabilities, years — use tabular figures.

## Accent

Teal marks links, the current destination, and numeric estimates. Amber marks qualitative views and the synthetic-data banner. Slate marks model-inferred signals. Warnings use a rust border. Color is paired with text or shape: probability points are filled circles, predicted years are squares, ranges are open strokes.

## Composition

- Primary navigation is one compact row: Activity, People, Topics, Statements, Trends, then Sources, Search, Data, and Method. Search in the header is a field, separate from those links.
- Prose stays near a 66-character measure. Charts and tables use the full column.
- A trend page leads with the question, the exact scope, the sample, and one chart. The panel repeats the question as a heading for the section, collapsed to a one-pixel accessible heading when the page title already states it. Method strings, stored keys, and cohort definitions sit in a disclosure after the evidence.
- Dataset status and the curator count strip are compact ledgers, not a stack of cards. The curator queue is an operator table. Record review places the source excerpt beside the interpretation on wide screens.

## Trust language

Synthetic fixtures say “Synthetic demo data” at the top of every page that renders the dataset. A corpus-read time is labeled as a read of stored records. It is not described as live collection.

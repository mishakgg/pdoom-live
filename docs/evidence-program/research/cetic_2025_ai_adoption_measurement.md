# Brazil: ICT Enterprises 2025 AI adoption measurement

## Main result and essential scope caveat

Cetic.br’s published H9 indicator is about **17%** for 2025. Its stored total-row value is **17.46%**, with a stored published percentage margin of **1.72**. The workbook formats both as whole numbers, displaying 17 and 2.

**The question was collected only among enterprises with IT specialists, an IT area or department, then published using total enterprises as the denominator.** This screening rule is essential to interpretation and comparison. The result is not an unqualified measurement asked of every Brazilian business.

Exact publisher footnote, H9!A23 in all four views:

“¹This indicator was collected only among enterprises with IT specialists, area or department. For dissemination purposes, the results are presented by the total number of enterprises.”

The H9!A2 denominator is “Total number of enterprises¹.” H9!A1 identifies artificial-intelligence technologies broadly; this is not a separately identified generative-AI or ChatGPT adoption rate.

## Exact evidence locations

All four readings are H9!C5, with “Yes” in C3/C4 and “Total” in B5. Units are the literal A3 labels:

| Workbook | A3 unit label | Stored C5 value |
|---|---|---:|
| ict_enterprises_2025_table_proportion_v1.0.xlsx | Percentage (%) | 17.46 |
| ict_enterprises_2025_table_sampling_error_v1.0.xlsx | Margin of error (%) | 1.72 |
| ict_enterprises_2025_table_total_v1.0.xlsx | Total | 93475 |
| ict_enterprises_2025_table_sampling_error_total_v1.0.xlsx | Margin of error for total | 9211 |

The margin is on the absolute percentage scale, conventionally percentage points. The total-margin/combined-enterprise-total reconciliation supports this interpretation. **The confidence level is not stated in these table cells; no 95% confidence interval is asserted.** The total 93,475 is a published enterprise estimate, not a respondent sample count.

The proportion and percentage-margin cells use custom number-format ID 165 with format code `0`. Retaining their stored decimals is useful for traceability; it does not establish extra statistical precision.

## Size breakdown, with the same screening caveat

| Source cell in each view | Category from column B | Stored percentage | Stored published percentage margin |
|---|---|---:|---:|
| H9!C6 | 10 to 49 employed persons | 14.86 | 1.805 |
| H9!C7 | 50 to 249 employed persons | 32.25 | 5.272 |
| H9!C8 | 250 or more employed persons | 49.57 | 3.869 |

These are descriptive subgroup estimates. A numerical gap is not presented as a causal effect or a formal significance result. Full population eligibility and design information require the survey methodology.

## H9A describes AI users

H9A!A2 explicitly reads “Total number of enterprises that used Artificial Intelligence technologies.” For example, workflow automation is 67.511 in the proportion workbook at H9A!H5, with margin 5.0724 at the same cell in the percentage-margin workbook. The H3/H4 column label is “Workflow automation.”

That is a share **among AI-using enterprises**, not overall enterprise adoption. H9A type shares exceed 100 when added, so they must not be treated as a partition. Natural-language generation is another publisher category; it should not automatically be relabeled as generative-AI prevalence. H9B/H9C/H10 are also AI-user-conditioned; H13 concerns non-users.

## Coverage and statistical limits

- The ZIP contains four aligned statistical views of 48 table IDs, yielding 192 worksheets. Those repeated views are not 192 independent tables or surveys.
- There are 6,069 matched aggregate cell locations: 6,018 numeric locations and 51 literal hyphens, each repeated across the four views. These are correlated survey aggregates, not independent training observations.
- Each table has 17 rows: one total, three size bands, five regions and eight market segments. Languages and file formats do not add independent survey evidence.
- Confidence level, standard errors, design covariance and unweighted sample sizes are not provided in the table text used here. No inferred confidence interval, p-value or trend is added.
- Preserve the hyphens; their formal meaning is not defined in these table cells. Do not silently treat them as zero.
- Table membership and four-view alignment are established for this archive. Completeness against the publisher’s broader questionnaire or release scope is not asserted.

## Public source and integrity

Source: [Cetic.br ICT Enterprises 2025 English XLSX tables v1.0](https://cetic.br/media/microdados/1039/ict_enterprises_2025_tables_xlsx_v1.0.zip).

Original archive size: 446,528 bytes.

Original archive SHA-256: `3c929537c2f30fb24eacdc4d7fb31faf1b1b6862af9655d09b86d9a11ae4311b`.

The accompanying JSON evidence catalog preserves workbook hashes, exact sheet/cell references, original unit labels, raw values, formatting metadata and the screening/uncertainty caveats. Derived evidence files are not additional source bytes.

Attribution: Brazilian Network Information Center (NIC.br), Cetic.br. (2026). *Survey on the use of information and communication technologies in Brazilian enterprises: ICT Enterprises 2025 [Tables].* The source tables are licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/deed.pt_BR).

Modification notice: This measurement note and its evidence catalog are derived analysis. Source numeric values, unit labels and cited wording remain unchanged. Selection, alignment, formatting descriptions and interpretive caveats have been added.

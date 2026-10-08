# Labor-market effects and skill demand

Reviewed 8 October 2026 against `mishakgg/pdoom-live@ab1434f30114df6784409d84069e9a8f785a45b1`. One submitted report, four curated collections: three new source families and one GL022 training-artifact enrichment. All remain unadmitted. The frozen 64-family inventory and all thirteen previous catalogs/readers/contracts are unchanged.

## Recommendation and boundaries

Top additions: BLS OEWS for employment/wage outcomes; Indeed AI Tracker for frequent AI-related advertisement text; Eurostat ICT training for enterprise skill investment. O*NET adds task measurement and historical-vintage context. None identifies a causal AI effect on employment or wages.

[Machine-readable catalog](../../../data/evidence-program/research/labor-market.json) · [Review queue](research-session-review-queue.md) · [Offline tools](../../../tools/evidence_program/README.md)

- No causal AI employment/wage estimate, individual profiling, legal advice, p(doom) or automatic exposure score.
- Source family, survey population, artifact/presentation, alternative estimate, measurement vintage and byte snapshot are different identity levels.
- No respondent/job-ad/person records, large archive downloads, source/model execution, live collection, canonical import or deployment.
- Rights cover exact artifacts, not proprietary job advertisements, every geography, website or all downstream presentations.
- Explicit missing values, years, flags, uncertainty and historical versions never silently become zero, current facts or corrected observations.

## LM001 BLS Occupational Employment and Wage Statistics

Identity: `bls-oews`; inventory relationship: `new_source_family_in_inspected_inventory_and_prior_catalogs`; existing source ID: `none`.

Survey-based modeled employment estimates and wage rates; no adoption-linked causal effects.

Coverage: Main national/state/area catalog 1997–May 2025; separate industry tables 1988–1995; nonmetropolitan data start May 2006. MB3 alternatives cover 2015–2020.

Cadence: Annual release; semiannual panel collection.

Population: Covered US full/part-time wage-and-salary jobs; self-employed, unincorporated owners/partners, household workers and unpaid family workers excluded.

Access: Public HTML and statistical downloads. May 2025 ZIP returns HEAD200 only; workbook contents/schema not inspected.

### Verified artifacts and scoped rights

- [lm001_catalog](https://www.bls.gov/oes/tables.htm): Historical release catalog. Locator: National/state/area years; separate industry series. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm001_release](https://www.bls.gov/news.release/archives/ocwage_05152026.htm): Dated May2025 estimates release. Locator: May15,2026 Table1, Software developers row. Access: `html_sample_verified`. Rights: `public_domain_statistical_material`. BLS statistical tables; images/emblems/third-party exceptions not included.
- [lm001_zip](https://www.bls.gov/oes/special-requests/oesm25nat.zip): National statistical workbook package. Locator: Catalog link and HEAD HTTP200; 279525 bytes advertised; body uninspected. Access: `headers_only`. Rights: `public_domain_statistical_material`. BLS-published statistical material; workbook content not inspected.
- [lm001_faq](https://www.bls.gov/oes/oes_ques.htm): Methods and time-series warnings. Locator: SOC/NAICS, panel rotation, wage processing, topcoding. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm001_concepts](https://www.bls.gov/opub/hom/oews/concepts.htm): Population/wage concepts. Locator: Covered jobs and wage-rate definitions. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm001_mb3](https://www.bls.gov/oes/oes-mb3-methods.htm): Alternative MB3 research estimates. Locator: 2015–2020 alternatives to published estimates. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm001_rights](https://www.bls.gov/opub/copyright-information.htm): Publisher reuse statement. Locator: Statistical material public domain; attribution requested; image/emblem exceptions. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm001_projections](https://www.bls.gov/emp/documentation/definitions.htm): Different BLS employment product. Locator: Employment Projections counts jobs including self-employment. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.

### Qualified findings

- The May 2025 Software developers row reports employment 1,687,890; mean hourly USD71.20; mean annual USD148,100; median hourly USD65.38. These are reviewer-normalized facts from HTML Table 1, not workbook column names. Published May 15,2026; wages are rates, not realized annual earnings. [lm001_release](https://www.bls.gov/news.release/archives/ocwage_05152026.htm) · [lm001_concepts](https://www.bls.gov/opub/hom/oews/concepts.htm)
- The May 2025 estimate pools six panel reference periods from November 2022 through May 2025. Four of six panels overlap adjacent annual releases, inferred from the documented rotation. Panel reference dates are not individual response dates. [lm001_release](https://www.bls.gov/news.release/archives/ocwage_05152026.htm) · [lm001_faq](https://www.bls.gov/oes/oes_ques.htm)
- 2019–2020 use hybrid 2010/2018 SOC; 2021 is fully 2018 SOC and introduces MB3; 2022 changes wage processing and adopts 2022 NAICS; 2025 exposes some previously top-coded percentiles. No title-only historical joins. Retain SOC and NAICS editions, geographic boundaries, suppression, uncertainty and estimation regime. [lm001_faq](https://www.bls.gov/oes/oes_ques.htm)
- National/state/area history reaches 1997, but nonmetropolitan series begin May 2006; separate industry estimates also exist for 1988–1995. This is not a balanced geography/occupation panel. Earlier occupational and industry definitions differ. [lm001_catalog](https://www.bls.gov/oes/tables.htm)
- MB3 research estimates for 2015–2020 are alternatives from shared survey evidence. Preserve the original and MB3 estimation regimes instead of silently overwriting or counting them as independent evidence. [lm001_mb3](https://www.bls.gov/oes/oes-mb3-methods.htm)
- BLS explicitly permits reuse of published statistical material in the public domain and requests source credit. The selected statistical table is covered; this does not waive image, emblem or third-party exceptions. [lm001_rights](https://www.bls.gov/opub/copyright-information.htm) · [lm001_release](https://www.bls.gov/news.release/archives/ocwage_05152026.htm)

### Interpretation limits

- Annualized wages generally use hourly rates times2080, with occupation-specific exceptions; not annual earnings or employee income.
- Survey pooling, sampling, modeling, inflation, occupation/industry recoding, geography and macroeconomic/labor-supply changes limit naive trends.
- No establishment AI-adoption/outcome linkage verified. Exposure-score joins are derived analyses, not observed AI effects.
- Workbook schema remains uninspected; ZIP header availability does not establish file integrity or sheet semantics.

## LM002 Indeed Hiring Lab AI Tracker

Identity: `indeed-ai-tracker`; inventory relationship: `new_source_family_in_inspected_inventory_and_prior_catalogs`; existing source ID: `none`.

Share of job postings containing AI-related text; not hiring, unique vacancies or pure occupational skill demand.

Coverage: Verified boundary dates 2019-01-01 through 2026-08-31 for AU,CA,DE,FR,GB,IE,IT,NL,US; interior completeness unaudited.

Cadence: Daily observations; seven-day trailing averages; monthly publication refreshes.

Population: Country-level Indeed advertised postings; coverage/denominator composition and multilingual matching may vary.

Access: Pinned GitHub CSV bounded line reads; raw endpoint advertised but not separately transferred in this pass.

### Verified artifacts and scoped rights

- [lm002_csv](https://github.com/hiring-lab/ai-tracker/blob/60a9ff5d2b6fd5c1cce4d130b0c7987af93c76c4/AI_posting.csv): Pinned country-level aggregate CSV. Locator: Header and first/last complete date blocks. Access: `bounded_csv_lines_verified`. Rights: `CC_BY_4_0_generated_aggregates`. Hiring Lab-generated aggregate data only; no underlying proprietary advertisements.
  Version: 60a9ff5d2b6fd5c1cce4d130b0c7987af93c76c4.
- [lm002_readme](https://github.com/hiring-lab/ai-tracker/blob/60a9ff5d2b6fd5c1cce4d130b0c7987af93c76c4/README.md): Methodology and data-license statement. Locator: Seven-day average, monthly updates, data terms; GenAI filename claim. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
  Version: 60a9ff5d2b6fd5c1cce4d130b0c7987af93c76c4.
- [lm002_tree](https://api.github.com/repos/hiring-lab/ai-tracker/git/trees/826fa1b67e2ad83b4572196b806a6a239a4d3205): Pinned repository tree. Locator: Four files, no GenAI_posting.csv or dictionary. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm002_canada](https://hiringlab.indeed.com/en-ca/2026/07/08/ontario-job-postings-highlight-the-widespread-use-of-ai-in-hiring-processes/): Publisher construct-break annotation. Locator: July8,2026; late2025 rise and monthly-averaged2026 comparisons. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm002_us_context](https://hiringlab.indeed.com/2025/10/28/how-employers-are-talking-about-ai-in-job-postings/): US sample thematic analysis. Locator: July2024–June2025 sample; recruitment and context categories. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm002_faq](https://hiringlab.indeed.com/indeed-data-faq-2/): Posting and deduplication limitations. Locator: Ads/openings/hiring and platform coverage. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm002_ccby](https://creativecommons.org/licenses/by/4.0/): CC BY terms. Locator: Attribution, license link, modifications. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.

### Qualified findings

- Pinned commit 60a9ff5d2b6fd5c1cce4d130b0c7987af93c76c4 remains current at inspection; committed September 10, 2026 at 02:54:27 UTC. CSV blob b5c97a719d62f8ba70dedcf2fb5b8ee683d912d2; no claim of ongoing freshness after inspection. [lm002_csv](https://github.com/hiring-lab/ai-tracker/blob/60a9ff5d2b6fd5c1cce4d130b0c7987af93c76c4/AI_posting.csv) · [lm002_tree](https://api.github.com/repos/hiring-lab/ai-tracker/git/trees/826fa1b67e2ad83b4572196b806a6a239a4d3205)
- CSV fields are date, jobcountry and AI_share_postings. US2019-01-01 is 1.71521638431397 and US2026-08-31 is 6.73985917144409 percent. Both date boundaries contain nine countries; interior completeness remains unverified. Percentages are not fractions or job counts. [lm002_csv](https://github.com/hiring-lab/ai-tracker/blob/60a9ff5d2b6fd5c1cce4d130b0c7987af93c76c4/AI_posting.csv)
- Daily country shares use seven-day trailing averaging and are refreshed monthly. Observation frequency, smoothing and refresh cadence are three distinct concepts. The CSV supplies no denominator count, occupation crosswalk or confidence interval. [lm002_readme](https://github.com/hiring-lab/ai-tracker/blob/60a9ff5d2b6fd5c1cce4d130b0c7987af93c76c4/README.md) · [lm002_csv](https://github.com/hiring-lab/ai-tracker/blob/60a9ff5d2b6fd5c1cce4d130b0c7987af93c76c4/AI_posting.csv)
- Indeed interprets Canada AI mentions in 2026 as primarily recruiting-AI disclosure text, with an anticipatory rise in late 2025. This is publisher measurement interpretation, not legal advice or independent legal-text verification. The Ontario legal page returned 403 and that route stayed stopped. Article comparisons are monthly averages, not daily CSV cells. [lm002_canada](https://hiringlab.indeed.com/en-ca/2026/07/08/ontario-job-postings-highlight-the-widespread-use-of-ai-in-hiring-processes/)
- A US sample analysis reports about 13.6% recruitment-tool mentions and roughly 25% without clear thematic fit among sampled AI-related postings. Several-hundred-thousand-posting sample from July 2024–June 2025; neither percentage is a correction factor for other countries/dates or a full keyword-version history. [lm002_us_context](https://hiringlab.indeed.com/2025/10/28/how-employers-are-talking-about-ai-in-job-postings/)
- GenAI_posting.csv is named in the README but absent from the complete pinned tree. Offer only the verified broad-AI artifact. Historical keyword dictionary version remains unknown; current absence does not prove absence from all past releases. [lm002_readme](https://github.com/hiring-lab/ai-tracker/blob/60a9ff5d2b6fd5c1cce4d130b0c7987af93c76c4/README.md) · [lm002_tree](https://api.github.com/repos/hiring-lab/ai-tracker/git/trees/826fa1b67e2ad83b4572196b806a6a239a4d3205)
- CC BY4.0 covers Hiring Lab-generated aggregate data with credit, license link and modifications notice. Underlying proprietary advertisements and unrelated third-party content do not inherit this clearance. Ads and deduplication are not unique vacancies or completed hiring. [lm002_readme](https://github.com/hiring-lab/ai-tracker/blob/60a9ff5d2b6fd5c1cce4d130b0c7987af93c76c4/README.md) · [lm002_ccby](https://creativecommons.org/licenses/by/4.0/) · [lm002_faq](https://hiringlab.indeed.com/indeed-data-faq-2/)

### Interpretation limits

- AI-related text can describe recruitment tools, task skills or boilerplate; maintain country/time-specific interpretation warnings.
- Platform coverage, ad composition and declining non-AI denominator can change shares without more AI hiring.
- One ad can represent several openings or remain after hiring. Deduplication is not exact vacancy counting.
- Dictionary version, country matching details, underlying denominators and uncertainty remain unknown; no occupational allocation or causal employment inference.

Attribution: selected values from Indeed Hiring Lab, AI Tracker, AI_posting.csv at the pinned September 10, 2026 commit, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Selected numerical values are unchanged; presentation and explanatory prose are adapted by pdoom.live. Underlying advertisements are excluded.

## LM003 Eurostat enterprise ICT-training tables

Identity: `eurostat-enterprise-ict-training`; inventory relationship: `enrichment_existing_source_family`; existing source ID: `GL022`.

Reported enterprise ICT-training provision; general ICT, not AI-specific skills, trained workers, hours or effectiveness.

Coverage: One verified German slice: survey years 2012,2014,2015,2016,2017,2018,2019,2020,2022,2024. No 2013,2021,2023 observations.

Cadence: Annual enterprise ICT survey with intermittent training module; source update 2026-06-15 T11:00:00+0200.

Population: DE; A; GE10; NACE Rev.2 C10-S951_X_K; E_ITT2; PC_ENT. Population scope changes require annotations. GE10 employed persons includes self-employed; this differs from OEWS wage-and-salary coverage.

Access: One 3,506-byte filtered JSON-stat response; offline reader and separately licensed fixture implemented; no refresh.

### Verified artifacts and scoped rights

- [lm003_slice](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_ske_ittn2?lang=en&geo=DE&size_emp=GE10&nace_r2=C10-S951_X_K&indic_is=E_ITT2&unit=PC_ENT): Exact bounded JSON-stat slice. Locator: Ten value indices; dimensions; status member absent; upstream timestamp. Access: `http200_exact_bytes_verified`. Rights: `statistical_data_reuse_with_attribution`. Selected German EU statistical data only; retain item-specific and third-party exceptions.
  Version: dab0f8f8f445839ac883543729ebb006118de10dc5893b9a1bed77bddf640c61.
- [lm003_table](https://ec.europa.eu/eurostat/databrowser/view/isoc_ske_ittn2/default/table?lang=en): Activity-table presentation. Locator: isoc_ske_ittn2. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm003_size_table](https://ec.europa.eu/eurostat/databrowser/view/isoc_ske_itts/default/table): Size-table companion presentation. Locator: Overlapping populations need cell-level deduplication. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm003_api_docs](https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-introduction): API revision and snapshot policy. Locator: Latest-version database; no past-version documentation. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm003_availability](https://ec.europa.eu/eurostat/documents/341889/725159/Variables%2Bsummary%2BENT2%2BSDMX%2Bincl%2B2024.pdf/a1959c27-52f1-0d3d-7955-53bbe791e209?t=1670238367252): Variable-availability matrix. Locator: Page18 E_ITT2 row in matrix2009–2025; bounded text review, no complete byte hash. Access: `primary_documentary_text_verified`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm003_metadata](https://ec.europa.eu/eurostat/cache/metadata/en/isoc_e_esms.htm): Survey and latest-only API methodology. Locator: Reference periods, population and country differences, revision policy. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
  Version: 5705acd8a20f5905e5c70d8afc54826813cf31f0743a12361727f1f82455a4e6.
- [lm003_reference](https://ec.europa.eu/eurostat/statistics-explained/SEPDF/cache/40327.pdf): Training reference-year documentation. Locator: Page9: survey2024 question covers calendar2023. Access: `pdf_page_visually_verified`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
  Version: b056b5cf026794abe9ee87d06b3469e00a714b873980ba4e069a86ba5e82ab6f.
- [lm003_rights](https://ec.europa.eu/eurostat/web/main/help/copyright-notice): Statistical-data reuse authorization. Locator: Data/metadata rights separate from editorial CC BY; geography exceptions. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
  Version: a07bd7c4e2d78de8a580c9854ce0ae7270db4400555250b5f4f6802c85cc5e7c.
- [lm003_desi](https://digital-decade-desi.digital-strategy.ec.europa.eu/datasets/desi/charts/desi-indicators?breakdown=ent_all_xfin&indicator=desi_eitt&period=desi_2025&unit=pc_ent): Downstream DESI presentation. Locator: Submitted derivative-presentation lead; specific current cell correspondence not independently reverified. Access: `current_js_shell_specific_cells_unverified`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.

### Qualified findings

- The exact filtered snapshot yields ten German survey-year observations, ending with 2024=26.41 percent. Earlier values 23.72,31.20,29.79,29.07,27.79,29.89,31.61,23.76,27.32 follow the explicit category indices. Missing years are not zero. [lm003_slice](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_ske_ittn2?lang=en&geo=DE&size_emp=GE10&nace_r2=C10-S951_X_K&indic_is=E_ITT2&unit=PC_ENT)
- The 2024 survey asks about ICT training in calendar 2023, documented on page 9. Earlier training reference years remain null until individually documented; no mechanical year-minus-one transformation. [lm003_reference](https://ec.europa.eu/eurostat/statistics-explained/SEPDF/cache/40327.pdf)
- Upstream update 2026-06-15, survey year 2024 and training reference year 2023 are separate; retrieval occurred October 8,2026. JSON-stat 2.0, dataset extension 1.0 and data-structure 43.0 are separate versions. No status member is supplied; missing status and uncertainty remain unknown, not false/zero. [lm003_slice](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_ske_ittn2?lang=en&geo=DE&size_emp=GE10&nace_r2=C10-S951_X_K&indic_is=E_ITT2&unit=PC_ENT) · [lm003_reference](https://ec.europa.eu/eurostat/statistics-explained/SEPDF/cache/40327.pdf)
- Activity scope changed in 2021, including veterinary activities; an unchanged aggregate NACE code does not guarantee identical populations. This is a population-comparability warning, not a quantified German-specific break. Country sampling/nonresponse and questionnaire implementation also differ. [lm003_metadata](https://ec.europa.eu/eurostat/cache/metadata/en/isoc_e_esms.htm)
- The API exposes latest dataset state without a historical dataset-revision archive. Persist exact bytes/hash and retrieval metadata; revisions use new snapshot keys while stable observation identities preserve table/dimensions/survey year. [lm003_api_docs](https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-introduction) · [lm003_slice](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_ske_ittn2?lang=en&geo=DE&size_emp=GE10&nace_r2=C10-S951_X_K&indic_is=E_ITT2&unit=PC_ENT)
- Eurostat permits selected German statistical-data reuse with source attribution; it is not the website editorial CC BY grant. Commercial geographic exceptions are narrower than all non-EU: EU/EFTA/official accession-candidate data have the stated permission. Do not generalize beyond this German selection or waive third-party exceptions. [lm003_rights](https://ec.europa.eu/eurostat/web/main/help/copyright-notice)
- Activity/size training presentations may reproduce overlapping Eurostat cells; GL022 AI-use has shared survey infrastructure. Keep table/indicator/dimension/version identities. Training and AI-use have no verified same-enterprise linkage or causal AI effect. Specific current DESI-cell duplication remains unverified. [lm003_table](https://ec.europa.eu/eurostat/databrowser/view/isoc_ske_ittn2/default/table?lang=en) · [lm003_size_table](https://ec.europa.eu/eurostat/databrowser/view/isoc_ske_itts/default/table) · [lm003_desi](https://digital-decade-desi.digital-strategy.ec.europa.eu/datasets/desi/charts/desi-indicators?breakdown=ent_all_xfin&indicator=desi_eitt&period=desi_2025&unit=pc_ent) · [lm003_metadata](https://ec.europa.eu/eurostat/cache/metadata/en/isoc_e_esms.htm)

### Interpretation limits

- The fraction is enterprises reporting training, not individual employees, hours, competence or effectiveness.
- General ICT is not AI-specific training. Aggregate aligned adoption/training shares do not identify the same firms.
- Intermittent observations and documented scope changes prohibit unqualified annual interpolation or homogeneous trends.
- Earlier reference periods, country-specific comparability and lossless canonical mapping remain held; no source admission.

## LM004 O*NET archived Task Ratings and update metadata

Identity: `onet-task-ratings`; inventory relationship: `new_source_family_in_inspected_inventory_and_prior_catalogs`; existing source ID: `none`.

Incumbent/expert occupational task importance, relevance and frequency distributions with source/vintage/uncertainty.

Coverage: Standalone Task Ratings introduced 13.0 inJune 2008; releases through 31.0 August 2026. Not a balanced occupation/task panel.

Cadence: Database approximately quarterly; occupation/rating refresh is uneven and may repeat unchanged measurements.

Population: US O*NET-SOC2019 occupational profiles for release 31.0; taxonomy and task-definition changes remain separate.

Access: Versioned task CSV206 partial response (2048 of 39006755 bytes); small category metadata; longitudinal workbook HEAD200 only.

### Verified artifacts and scoped rights

- [lm004_database](https://www.onetcenter.org/database.html): Current database description. Locator: Current31.0 production release and update frequency. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm004_archive](https://www.onetcenter.org/db_releases.html): Historical database releases. Locator: 13.0June2008 Task Ratings introduction;31.0August2026. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm004_ratings](https://www.onetcenter.org/dl_files/database/db_31_0_csv/task_ratings.csv): Versioned rating data. Locator: First complete record only; trailing incomplete prefix row ignored. Access: `http206_bounded_sample_verified`. Rights: `CC_BY_4_0_database`. O*NET31.0 downloadable database; not every website/tool.
- [lm004_dictionary](https://www.onetcenter.org/dictionary/31.0/csv/task_ratings.html): Task Ratings schema. Locator: Fields, date definition, uncertainty and suppression. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm004_categories](https://www.onetcenter.org/dictionary/31.0/csv/task_categories.html): Frequency category dictionary. Locator: FT category1 means Yearly or less. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm004_updates](https://www.onetcenter.org/dl_files/Longitudinal_Data_Updates.xlsx): Longitudinal update workbook. Locator: Official link/HEAD200; workbook uninspected. Access: `headers_only`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm004_changes](https://www.onetcenter.org/dictionary/30.3/text/appendix_updates.html): Historical changes. Locator: 29.0 relevance threshold;29.3 emerging tasks;25.1 transitions. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm004_rights](https://www.onetcenter.org/license_db.html): Downloadable database license. Locator: CC BY4.0/version attribution; earlier versions permitted under this or original terms. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.
- [lm004_occupation](https://www.onetonline.org/link/summary/15-1252.00): Software Developer secondary product display. Locator: Wages credited to OEWS; employment credited to Employment Projections. Access: `primary_documentary_review`. Rights: `unknown`. This artifact only; no blanket rights to underlying records or linked third-party materials.

### Qualified findings

- Release 31.0 August 2026 repeats the inspected Chief Executives 11-1011.00 task 8823 FT category 1 row updated 08/2023, source Incumbent. Frequency response value 5.92%, N76, SE4.2651, lower 95 CI1.3474, upper 95 CI22.4442, suppressN. Category 1 is Yearly or less; not percent of working time. [lm004_ratings](https://www.onetcenter.org/dl_files/database/db_31_0_csv/task_ratings.csv) · [lm004_dictionary](https://www.onetcenter.org/dictionary/31.0/csv/task_ratings.html) · [lm004_categories](https://www.onetcenter.org/dictionary/31.0/csv/task_categories.html)
- Database release date and row update date are not exact fieldwork dates. A later release carrying an unchanged rating vintage is republication, not a new measurement. Preserve taxonomy, task wording/ID, source, uncertainty and suppression. [lm004_dictionary](https://www.onetcenter.org/dictionary/31.0/csv/task_ratings.html) · [lm004_archive](https://www.onetcenter.org/db_releases.html)
- Release 29.0 August 2024 increased task-retention relevance from 10% to 25%. Task disappearance at this boundary does not establish AI replacement, job loss or changed working time. [lm004_changes](https://www.onetcenter.org/dictionary/30.3/text/appendix_updates.html)
- Release 25.1 introduced taxonomy-transition aggregates from predecessor occupations; 29.3 added AI/SME drone-related Emerging Tasks. Keep transitional, expert, incumbent and AI/SME evidence distinct. The inspected incumbent Task Ratings row is not shown to be AI-generated. [lm004_changes](https://www.onetcenter.org/dictionary/30.3/text/appendix_updates.html) · [lm004_ratings](https://www.onetcenter.org/dl_files/database/db_31_0_csv/task_ratings.csv)
- O*NET Software Developers wages include the BLS OEWS2025 median hourly USD65.38; its employment 1,717,800 comes from Employment Projections. OEWS employment 1,687,890 is a different product/population concept. Do not overwrite either value or explain the entire difference as self-employment without reconciliation. [lm004_occupation](https://www.onetonline.org/link/summary/15-1252.00)
- Downloadable O*NET database files are CC BY4.0, with version-specific O*NET/USDOL/ETA credit, license link and modifications notice. Earlier versions may use this or their original license. Developer registration is optional; broad website/tools rights are not inferred. [lm004_rights](https://www.onetcenter.org/license_db.html)

### Interpretation limits

- FT distributions are respondent frequency-category percentages, not task time allocation or AI exposure.
- Uneven update dates and unchanged repeated ratings do not form a balanced quarterly measurement panel.
- Taxonomy, task wording, threshold and respondent-source changes can resemble real change in work.
- Longitudinal workbook schema and historical crosswalks remain uninspected. Task-description-based AI exposure is separate derived evidence.

Attribution: selected data from the O*NET® 31.0 Database by USDOL/ETA, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). O*NET® is a USDOL/ETA trademark. Fields are selected and described in prose by pdoom.live; USDOL/ETA has not approved, endorsed or tested these adaptations. No raw Task Ratings file is republished.

## Held Census BTOS workforce supplement

This remains a held GL023/AP005 enrichment, not a fifth shortlisted or admitted collection. The two Content V4 Cycle 2 questionnaires revised 23 July 2025 have distinct bytes but whitespace-normalized text matches. Q28 employment effects and Q29 training/hiring are further item coverage in the existing survey; respondent attributions are not causal identification.

[Workforce questionnaire](https://www2.census.gov/data/experimental-data-products/business-trends-and-outlook-survey/questionnaire-ai-supplement.pdf) · [Previously cataloged mirror](https://www.census.gov/hfp/btos/downloads/BTOS%20Core%20and%20AI%20Content.pdf)

No workbook retrieval was attempted in this review. The submitted report claimed HTTP 403 but supplied no exact workbook URL; prior AP005 verification instead recorded a National.xlsx web Internal Error with no body or headers. These are separate attributed outcomes, not a fresh verified 403. No blocked route was retried or bypassed. Exact workbook rights, schema, denominator and flags remain unknown. A blank questionnaire is not evidence of observed workforce cells.

## Identity and all-catalog overlap review

Compared frozen inventory version 1.1 (64 families), all 13 earlier catalogs, 70 prior collections and 505 artifact references. There are 65 candidate-by-catalog assessments: the four shortlist collections plus the held BTOS lead against each prior catalog. These are scoped reviews, not proof about every unseen source or respondent.

Generic license-page matches are not duplicate data: the CC BY URL is shared with the concentration, organizational-safety and scientific-progress catalogs. The matrix URL fields compare selected data/artifact URLs, not every documentation or rights link.

- `data/evidence-program/research/adoption-productivity.json`: National business adoption aggregates and linked-productivity associations (AP001) and selected workplace productivity studies (AP002–AP004) are related context, not identical labor-market series or observed jobs/wages/task-rating cells. AP005 is the existing Census BTOS family and the held workforce extension reuses its questionnaire/survey, so no fifth new family is admitted.
- `data/evidence-program/research/agent-security-incidents.json`: AgentDojo, AIxCC, tau-bench, METR horizons, NHTSA crash/recall records, OAIC/ART cases and a deployment postmortem concern benchmark reliability/incidents. No identical shortlisted source artifact, labor survey, sample, or measurement cell was cataloged. Benchmark task outcomes are not O*NET occupational task ratings.
- `data/evidence-program/research/algorithmic-efficiency.json`: AlgoPerf, Modded-NanoGPT, Epoch language-model progress, OpenAI AI-and-Efficiency and FutureTech measure training efficiency/cost under protocol regimes, not employee training or labor outcomes. Shared terms such as training and task establish no dataset identity.
- `data/evidence-program/research/chinese-safety-evaluations.json`: Eight Chinese safety evaluation families contain questions/prompts/protocols and reported model results. They do not supply any of the four labor-market artifacts or Census workforce questionnaire. Language/region references do not establish overlapping survey evidence.
- `data/evidence-program/research/concentration-dependencies.json`: ATRS deployments, deps.dev dependencies, Bank/FCA surveys, OMB COTS and FTC partnerships measure procurement/concentration or financial-sector AI adoption. Bank/FCA employer survey is a different frame and instrument from Eurostat enterprise ICT training and BTOS; no matching study or cell is established.
- `data/evidence-program/research/historical-capability-backfills.json`: IPC, WMT, TREC, SAT and PASCAL VOC historical competitions measure system performance under benchmark definitions. Task labels do not equate to O*NET respondent-rated occupational tasks; no artifact/study/survey-cell duplicate found.
- `data/evidence-program/research/human-reliance.json`: Student and human-AI experimental outcomes in HR001–HR005 are specific participant studies, not representative labor-market or enterprise-training observations. Skills/training language is topical only; no identical participant study/artifact/cell cataloged.
- `data/evidence-program/research/open-model-diffusion.json`: Hub metadata, EOSAI, Epoch accessibility, OLMo artifacts and PeaTMOSS are model/software release or reuse measurements. Their training metadata is not employee ICT training, job-ad language or wages. No matching source artifact or measurement cell.
- `data/evidence-program/research/organizational-safety.json`: HAIP reports and developer governance records measure organizational reporting/controls. Workforce-training discussion within a report would not make it the Eurostat survey, OEWS estimate or O*NET task-rating study. No identical source artifact/study/cell found.
- `data/evidence-program/research/persuasion-information.json`: PI001–PI005 concern persuasion experiments and Ofcom information surveys. They have different instruments/outcomes/frames than employee training and labor-market estimates. No cataloged common study, artifact or cell; coincident individuals are not assessed.
- `data/evidence-program/research/robotics-physical.json`: BARN, RoboArena, TriFinger, PhAIL and STRANDS measure physical robotics performance and field-operation metrics. Robot training or labor-saving speculation is not occupational employment, wage data, employee training, or respondent task frequencies.
- `data/evidence-program/research/scientific-progress.json`: AI-Games, A-Lab, RE-Bench, AlphaTensor and CASP concern research outcomes/benchmarks. Their human work or compute inputs are not national employment, job postings, enterprise ICT training or O*NET task-rating samples; no exact artifact/study/cell duplication found.
- `data/evidence-program/research/training-data-feedback.json`: Common Crawl, DPI/Consent, synthetic-feedback experiments, FineWeb2 and Epoch data stock measure corpora and model-training inputs. Model training and workforce training are separate constructs. No exact labor-market artifact/study/cell duplicate.
- same_survey_family_distinct_variables: Keep AI use and ICT training separate table/indicator identities. Correlated aggregate country-size-industry shares do not establish same firms or a causal link.
- related_business_context_not_identical_study: StatCan CSBC retrospective adoption, SDTIU-linked administrative productivity, Indeed advertisement text and Eurostat training use different programs/frames/denominators. Do not join on Canada/period as if employer identifiers existed.
- same_survey_and_semantically_equivalent_questionnaire: Fresh two PDFs have different SHA256 but whitespace-normalized extracted text is identical; maintain distinct artifact hashes plus mirror/version relationship. Q28 employment effect and Q29 training/hiring are respondent attributions, not causal identification; no fifth admission.
- downstream_wage_republication_and_distinct_employment_product: O*NET wage display sources BLS OEWS; O*NET employment/projections display sources BLS Employment Projections. Do not double count wages or reconcile 1,717,800 vs 1,687,890 as a typo/AI effect.
- alternative_estimates_shared_survey: OEWS MB3 research 2015–2020 and original releases are same underlying survey family, with distinct estimation regimes/revisions.
- tracker_csv_visualizations_and_articles: Same country-day posting series is one evidence family. Separate US contextual sample analysis is a methodological annotation, not a universal adjustment or independent set of hiring observations.
- companion_table_overlap: isoc_ske_ittn2 and isoc_ske_itts presentations can overlap in underlying cells; match full dimensions and publication version before merging. Specific current DESI-cell relationship not independently reverified.
- repeated_rating_vintage: Unchanged task ratings in later database releases are republications, not new fieldwork. Emerging Tasks are separate evidence type.
- possible_downstream_synthesis_unverified: No particular AI Index artifact was verified to duplicate these series; do not turn shared institution/source mentions into confirmed overlap.

## Implemented offline slice

The [reader](../../../tools/evidence_program/read_eurostat_ict_training.py) consumes only local bytes and a reviewed manifest, or two fixed filenames under an explicit directory. It never fetches URLs, follows source links, executes annotation XML, writes files, runs models or imports canonical data. The one source fixture is outside `data/CC0` with [separate attribution and reuse notice](../../../tools/evidence_program/tests/fixtures/labor-market/NOTICE.md).

- Scope: ISOC_SKE_ITTN2; DE; annual A; GE10; C10-S951_X_K; E_ITT2; PC_ENT; survey years within 2012–2024. Additional dimensions/populations and unreviewed DSD versions are rejected.
- Bounds: 32,768 source bytes, 4,096 manifest bytes, 4,000 JSON nodes, depth 16 and at most 13 cells. Fixed local filenames only; symlink/traversal and duplicate-key rejection. Decimal tokens are bounded to 64 characters and validated exactly before conversion; precision loss, overflow and underflow are rejected.
- Decoding: explicit id/size/category bijections; dimension and category order can change. Dense arrays and sparse numeric maps are supported. Missing sparse cell, explicit null, observed zero, absent survey year, missing status member/cell and reported flag remain distinct.
- Provenance: raw SHA-256, retrieval time, original upstream update/timezone, JSON-stat version, dataset extension, DSD version, labels and inert source extension remain. Stable observation identity is separate from byte snapshot identity; new retrieval alone is not a new measurement.
- Semantics: percent of enterprises, general ICT training, survey year, verified 2024→2023 reference mapping, unknown earlier reference years, null uncertainty and population-comparability warnings. No interpolation, trend, exposure or causal-risk estimate.
- Actual acceptance: one 3,506-byte licensed aggregate response with ten observations and 2024=26.41. No status member is present. The 2026 update date is not a 2026 training outcome. Source OBS_COUNT=87309 describes the whole dataset, not acquired cells; source-created2022 is dissemination-object metadata, not the first survey year2012.

The original one-request acquisition proposal is not implemented as a network adapter. There is no refresh job, scheduling, broader API crawl, BLS/Indeed/O*NET reader or canonical mapping. Rights and operational admission remain separate from successful parsing.

## Corrections to the submitted shortlist

- BLS national/state/area history is not every-geography coverage from1997; nonmetropolitan begins2006; older industry tables have distinct scope.
- BLS panel reference periods are not exact response dates; overlap is arithmetic from rotation; annual wages are wage rates.
- Indeed boundary completeness does not imply complete interior; raw endpoint availability was not independently retransferred in this pass.
- Indeed Canada break is source-attributed measurement interpretation; inaccessible Ontario legal page remains unverified; no legal conclusion.
- Indeed US thematic13.6%/25% refer to a sampled population, not transferable adjustment coefficients.
- Eurostat rights are statistical-data authorization, not editorial CC BY; geography exceptions narrower than all nonEU.
- Eurostat no status member means absent, not no quality concern; JSON-stat2.0/dataset1.0/DSD43.0 remain separate.
- Eurostat API is latest-only; retrieved snapshots preserve revisions; only2024→2023 reference period is documented.
- O*NET FT category1 means Yearly or less, not percent working time. Fieldwork timing is unknown.
- O*NET29.3 AI/SME Emerging Tasks are separate from the incumbent rating;29.0 retention threshold creates a break.
- O*NET employment republication is BLS Employment Projections, distinct from OEWS. Do not force reconciliation.
- BTOS workforce content enriches held GL023/AP005 rather than a fifth newly admitted family.
- Current DESI exact cell correspondence was not independently reverified; keep it a derivative-presentation lead, not confirmed duplicate observations.

## Open holds

- Operational source admission, canonical lossless mapping, wider collection and deployment.
- BLS national workbook schema/contents, historical SOC/NAICS/geography crosswalks, suppression and uncertainty.
- Indeed interior completeness, historical dictionary versions, denominator/uncertainty and separately held legal text; no keyword correction coefficients.
- Eurostat earlier questionnaire reference years, population/country comparability and every wider geography/artifact-specific rights review.
- O*NET longitudinal-update workbook and historical rating/task/taxonomy linkage; no assumed fresh measurement in every release.
- Census workforce export access/schema, cell flags/denominators, instrument regimes and exact artifact rights; denied route remains stopped.
- AI Index GL034 derivative overlap remains unknown until a specific source-linked artifact is verified.

## Next actions

- LM-A01 Complete four-family and prior-catalog review — `completed_bounded_review`. Frozen64 and all13 catalogs,70 prior collections,505 artifact references and65 candidate-by-catalog comparisons including the held BTOS lead.
- LM-A02 Implement bounded offline Eurostat reader — `completed_offline_implementation`. One licensed aggregate fixture; dimension-aware sparse/dense decoding, flags, three clocks, exact decimal guard and revision identity; no acquisition/refresh job.
- LM-A03 Verify BLS workbook schema — `held_documentary_review`. See LM-P01.
- LM-A04 Verify Indeed measurement versions — `held_documentary_review`. See LM-P02.
- LM-A05 Verify Eurostat historical questionnaires — `held_documentary_review`. See LM-P03.
- LM-A06 Verify O*NET rating lineage — `held_documentary_review`. See LM-P04.
- LM-A07 Verify held BTOS export — `held_documentary_review`. See LM-P05.
- LM-A08 Verify derivative evidence links — `held_documentary_review`. See LM-P06.
- LM-A09 Review lossless labor mapping — `held_documentary_review`. See LM-P07.

## Standalone bounded follow-up prompts

Prepared assignments only; none has been dispatched or scheduled.

### LM-P01 Verify BLS workbook schema

Read-only primary-source research for mishakgg/pdoom-live. First read docs/evidence-program/research/labor-market.md and data/evidence-program/research/labor-market.json on current main and record the commit; disclose inaccessible files. Inspect at most one officially linked May 2025 national OEWS workbook only if access and artifact-specific rights permit a bounded statistical-file read. Record sheet/header, occupation/SOC and NAICS editions, employment/wage units, error/suppression/topcode fields and two complete nonpersonal aggregate rows including Software developers. Do not treat HEAD200 as contents or a wage rate as annual earnings. Compare 2015–2020 MB3 with ordinary estimates only as alternative regimes; no broad historical download. Return source/artifact URLs, precise evidence locators, access limits, artifact-specific rights, corrections and explicit unknowns. No login, outreach, access bypass, respondent/job-ad/person records, bulk downloads, source/model execution, repository edits, scheduled collection or deployment. Stop any denied route and report it. No causal AI employment claim, automatic exposure score, legal advice or p(doom).

### LM-P02 Verify Indeed measurement versions

Read-only primary-source research for mishakgg/pdoom-live. First read docs/evidence-program/research/labor-market.md and data/evidence-program/research/labor-market.json on current main and record the commit; disclose inaccessible files. Review one pinned AI Tracker README, tree and at most two small aggregate CSV windows at current and one historical commit. Document country/date boundaries, any dictionary/version explanation, percentage units, seven-day smoothing, monthly refresh and Canada late 2025/2026 construct break. Do not acquire underlying advertisements or infer occupation-level hiring; do not retry the blocked Ontario legal page or advertise absent GenAI_posting.csv. Keep context-study percentages separate from correction factors. Return source/artifact URLs, precise evidence locators, access limits, artifact-specific rights, corrections and explicit unknowns. No login, outreach, access bypass, respondent/job-ad/person records, bulk downloads, source/model execution, repository edits, scheduled collection or deployment. Stop any denied route and report it. No causal AI employment claim, automatic exposure score, legal advice or p(doom).

### LM-P03 Verify Eurostat historical questionnaires

Read-only primary-source research for mishakgg/pdoom-live. First read docs/evidence-program/research/labor-market.md and data/evidence-program/research/labor-market.json on current main and record the commit; disclose inaccessible files. Inspect at most two official enterprise ICT questionnaires for selected earlier survey years from 2012,2014–2020,2022. Establish the precise training reference period and E_ITT2 definition with evidence; leave other years unknown. Record GE10 and NACE population scope, country notes and 2021 veterinary-activity addition without inferring a quantified German break. No further API data query, year-minus-one batch rule or same-enterprise AI-adoption link. Return source/artifact URLs, precise evidence locators, access limits, artifact-specific rights, corrections and explicit unknowns. No login, outreach, access bypass, respondent/job-ad/person records, bulk downloads, source/model execution, repository edits, scheduled collection or deployment. Stop any denied route and report it. No causal AI employment claim, automatic exposure score, legal advice or p(doom).

### LM-P04 Verify O*NET rating lineage

Read-only primary-source research for mishakgg/pdoom-live. First read docs/evidence-program/research/labor-market.md and data/evidence-program/research/labor-market.json on current main and record the commit; disclose inaccessible files. Read one current 31.0 and one older release dictionary/update description plus at most two complete Task Ratings aggregate rows, or a bounded officially licensed longitudinal metadata sheet. Preserve O*NET-SOC2019/current versus historical taxonomy, task wording/ID, source/update date/unknown fieldwork, uncertainty/suppression, FT frequency category and 29.0 relevance-threshold change. Separate AI/SME Emerging Tasks, predecessor transitions and unchanged repeated measurement vintages. No large archive. Return source/artifact URLs, precise evidence locators, access limits, artifact-specific rights, corrections and explicit unknowns. No login, outreach, access bypass, respondent/job-ad/person records, bulk downloads, source/model execution, repository edits, scheduled collection or deployment. Stop any denied route and report it. No causal AI employment claim, automatic exposure score, legal advice or p(doom).

### LM-P05 Verify held BTOS export

Read-only primary-source research for mishakgg/pdoom-live. First read docs/evidence-program/research/labor-market.md and data/evidence-program/research/labor-market.json on current main and record the commit; disclose inaccessible files. Keep GL023/AP005 workforce supplement held. Review official documentation and any newly provided authorized export metadata for Q28/Q29, with question conditioning, recall period, uncertainty/suppression and exact file reuse rights. The two Content V4 Cycle 2 questionnaires are semantically matching but have different hashes. The submitted report claimed HTTP403 at an unspecified workbook URL; prior AP005 recorded National.xlsx web Internal Error without body or headers. No current workbook attempt was made. Do not retry or route around a previously blocked route. If no newly authorized artifact is supplied, return the access/rights blocker; do not infer data cells from questionnaire text or count a fifth source family. Return source/artifact URLs, precise evidence locators, access limits, artifact-specific rights, corrections and explicit unknowns. No login, outreach, access bypass, respondent/job-ad/person records, bulk downloads, source/model execution, repository edits, scheduled collection or deployment. Stop any denied route and report it. No causal AI employment claim, automatic exposure score, legal advice or p(doom).

### LM-P06 Verify derivative evidence links

Read-only primary-source research for mishakgg/pdoom-live. First read docs/evidence-program/research/labor-market.md and data/evidence-program/research/labor-market.json on current main and record the commit; disclose inaccessible files. Inspect at most one specific DESI indicator artifact and one specific AI Index GL034 source note using authorized primary documents. Confirm or leave unknown the original producer, table, dimensions, period, estimation regime and byte/version relationship. Exact current DESI cells and AI Index duplication remain unverified. Preserve O*NET wage republication from OEWS versus its distinct Employment Projections count; no forced numerical reconciliation or independent-evidence double count. Return source/artifact URLs, precise evidence locators, access limits, artifact-specific rights, corrections and explicit unknowns. No login, outreach, access bypass, respondent/job-ad/person records, bulk downloads, source/model execution, repository edits, scheduled collection or deployment. Stop any denied route and report it. No causal AI employment claim, automatic exposure score, legal advice or p(doom).

### LM-P07 Review lossless labor mapping

Read-only primary-source research for mishakgg/pdoom-live. First read docs/evidence-program/research/labor-market.md and data/evidence-program/research/labor-market.json on current main and record the commit; disclose inaccessible files. Read existing proposed evidence contracts and the offline Eurostat reader without executing external source programs. Produce a field-by-field mapping for source/table/population/dimensions, status/missingness, survey/reference/update/retrieval clocks, uncertainty, rights, stable observation key and byte snapshot identity. Separate BLS alternative estimation regimes, Indeed text constructs and O*NET rating vintage. Document gaps rather than modifying canonical schema, admitting sources or starting imports. Return source/artifact URLs, precise evidence locators, access limits, artifact-specific rights, corrections and explicit unknowns. No login, outreach, access bypass, respondent/job-ad/person records, bulk downloads, source/model execution, repository edits, scheduled collection or deployment. Stop any denied route and report it. No causal AI employment claim, automatic exposure score, legal advice or p(doom).


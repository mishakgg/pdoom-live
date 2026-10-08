# One bounded ICT-training slice

Exact licensed aggregate input and a separate local provenance manifest. See [NOTICE.md](NOTICE.md) for attribution and reuse scope. Run the offline reader with this directory; it opens only `de-ict-training.json` and `manifest.json`, rejects symlinks/oversize inputs, and makes no network calls.

The snapshot has survey years 2012, 2014–2020, 2022 and 2024; values 23.72, 31.20, 29.79, 29.07, 27.79, 29.89, 31.61, 23.76, 27.32 and 26.41 percent. No `status` member is supplied, so status remains unknown/absent, not false or zero. Earlier reference years remain unverified; only survey 2024 is documented to refer to training in calendar 2023. Latest-only API changes must be saved as new hashed snapshots.

Mutated inputs in tests are self-authored synthetic variants of this structure; they are never treated as newly observed data. No refresh job or canonical import is implemented.

# Third-party OSAI annotation fixtures: CC BY 4.0

The two YAML files in this directory are real, byte-preserved annotation files,
not synthetic examples. They are separately licensed third-party test fixtures
outside the repository's `data/` CC0 dedication. Their original license and
attribution headers are preserved without modification.

Source: EU Open Source AI Index, https://osai-index.eu/.
Repository: https://github.com/Language-Technology-Assessment/main-database.
Source path for both files: `llama-3.3.yaml`.

- `before-llama-3.3.yaml`: commit `e39b4edd41811e975f9262d77ee286796d7792e5`,
  Git blob `ce4e77557ac41d97ec59d872a2d6b7f19229ecdb`, 3,648 bytes,
  SHA-256 `89d1f517d5171d832c59359e83d6c7b7577aaf0c14f8a06c08b01adbbcdfcc17`.
- `after-llama-3.3.yaml`: commit `ff85b6ff442035e41c9492cefa54f78be0b827fc`,
  Git blob `855671b61e19ccdefa95879c0d85a4c5eb77dc5f`, 3,398 bytes,
  SHA-256 `cc93e48df6a72c3e15d05ae2a056fcf775d4ccf7c590bc26c13ebbdb9fea6ec8`.

Both fixtures were acquired at `2026-10-08T00:20:44Z` through the GitHub
connector `fetch_file`, preserving its exact base64-decoded file bytes. This is
original fixture acquisition time, not the current offline reader execution,
model release, or annotation assessment time.

The annotation data is licensed under Creative Commons Attribution 4.0
International: https://creativecommons.org/licenses/by/4.0/.
Legal code: https://creativecommons.org/licenses/by/4.0/legalcode.
There are no modifications to either YAML file. Parser output is a separately
identified experimental representation; it retains the original YAML text.

Required attribution from the fixture headers:

Liesenfeld, A. and Dingemanse, M., 2024. Rethinking open source generative AI:
open-washing and the EU AI Act. In Proceedings of the 2024 ACM Conference on
Fairness, Accountability, and Transparency (pp. 1774-1787).

Index-files citation, additionally requested by the upstream README at commit
`83011c306a1565ee1a6ecf4c881f09caa118d7e9`:
https://doi.org/10.5281/zenodo.15386042.

This permission concerns the annotation files only. It does not convey rights
to the model weights, model code, papers, model cards, or other linked works.
The annotation's `endmodellicense` value, "Llama 3.3 Community License Agreement,"
is separate from the annotation dataset's CC BY 4.0 license. No upstream
endorsement is implied. Links are attribution/provenance references, not
instructions to fetch their targets. Operational collection, source admission,
production import and model execution remain disabled.

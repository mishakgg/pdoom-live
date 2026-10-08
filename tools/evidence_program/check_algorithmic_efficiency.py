"""Offline curated algorithmic-efficiency research and licensed fixture checks."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qsl

BASE = "664963c472222c845d3068df898f7537c285ad28"
IDS = {f"AE{i:03}" for i in range(1, 6)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def safe_url(value):
    require(type(value) is str and 0 < len(value) <= 2048, "Unbounded URL")
    p = urlsplit(value)
    require(p.scheme == "https" and p.hostname and not p.username and not p.password
            and not any(c.isspace() for c in value), "Invalid source URL")
    require(not any(any(word in k.lower() for word in ["token", "secret", "credential", "signature", "api_key"])
                    for k, _ in parse_qsl(p.query)), "Private source URL")


def check_catalog(catalog, inventory_hash, markdown, root=None):
    require(type(catalog) is dict and set(catalog) == set(SECTIONS) | {"collections", "catalog_overlap_review"},
            "Reviewed catalog shape changed")
    require(catalog["repository_review_commit"] == BASE, "Wrong review base")
    require(catalog["baseline_inventory"]["sha256"] == inventory_hash, "Frozen inventory changed")
    for key, expected in SECTIONS.items():
        require(fingerprint(catalog[key]) == expected, "Reviewed section drift: " + key)
    rows = catalog["collections"]
    require(type(rows) is list and len(rows) == 5 and {x["candidate_id"] for x in rows} == IDS,
            "Five distinct source families required")
    require(len({x["source_family_id"] for x in rows}) == 5, "Source families merged")
    refs, findings = {}, set()
    for row in rows:
        cid = row["candidate_id"]
        require(fingerprint(row) == FAMILIES[cid], "Reviewed family semantics changed: " + cid)
        require(row["inventory_source_id"] is None and row["operational_admission"] == "not_admitted"
                and row["collector_enabled"] is False, "Research admission changed")
        local = {a["artifact_id"] for a in row["artifacts"]}
        for a in row["artifacts"]:
            require(a["artifact_id"] not in refs, "Duplicate artifact identity")
            refs[a["artifact_id"]] = a
            safe_url(a["url"])
            require(a["access_status"] and a["rights_scope"] and a["evidence_locator"], "Artifact evidence missing")
            require(a["rights_status"] in {"unknown", "declared_license", "declared_deposit_license_reuse_unresolved"}, "Unknown rights state")
            if a["rights_status"] != "unknown":
                require(a["license_identifier"] and a["rights_evidence_url"], "License evidence missing")
                safe_url(a["rights_evidence_url"])
            for field, length in [("git_commit", 40), ("git_blob_sha", 40), ("sha256", 64), ("fixture_sha256", 64)]:
                if a.get(field) is not None:
                    require(re.fullmatch("[a-f0-9]{" + str(length) + "}", a[field]), "Invalid source/derivative hash")
            if a["source_bytes_vendored"]:
                require(cid == "AE001" and a["license_identifier"] == "Apache-2.0"
                        and a["fixture_path"].startswith("tools/evidence_program/tests/fixtures/algorithmic-efficiency/"),
                        "Unknown-rights bytes or data/CC0 contamination")
            if a.get("fixture_retention") == "curated_allowlist_derivative":
                require(a["source_bytes_vendored"] is False and a["fixture_sha256"] != a["sha256"],
                        "Derivative represented as original")
        for conflict in row.get("source_conflicts", []):
            if "artifacts" in conflict:
                require(conflict["artifacts"] and set(conflict["artifacts"]) <= local,
                        "Dangling nested source-conflict reference")
        for estimate in row.get("estimates", []):
            require(estimate["evidence_artifact_id"] in local, "Dangling estimate evidence reference")
        for f in row["findings"]:
            require(f["finding_id"] not in findings and f["claim"] and f["qualification"], "Duplicate or empty finding")
            findings.add(f["finding_id"])
            require(f["evidence_artifact_ids"] and set(f["evidence_artifact_ids"]) <= local, "Missing finding evidence")
    overlap = catalog["catalog_overlap_review"]
    require(fingerprint(overlap) == OVERLAP, "Overlap review drift")
    require(overlap["commit"] == BASE and overlap["prior_collection_count"] == 58
            and overlap["prior_artifact_reference_count"] == 429 and overlap["comparison_cell_count"] == 55,
            "Incomplete prior catalog comparison")
    prior = overlap["catalogs_compared"]
    require(len(prior) == 11 and len({x["path"] for x in prior}) == 11, "Missing or duplicate prior catalog")
    for item in prior:
        require(set(item["candidate_checks"]) == IDS, "Missing candidate/catalog cell")
        if root is not None:
            raw = (Path(root) / item["path"]).read_bytes()
            require(hashlib.sha256(raw).hexdigest() == item["sha256"] and blob(raw) == item["git_blob_sha"],
                    "Earlier catalog changed")
            old = json.loads(raw); oldrows = old.get("collections", old.get("families", []))
            require(len(oldrows) == item["collection_count"] and
                    sum(len(x["artifacts"]) for x in oldrows) == item["artifact_count"], "Earlier counts changed")
    prompts = catalog["focused_follow_up_prompts"]
    require(len(prompts) == 6 and len({p["prompt_id"] for p in prompts}) == 6, "Follow-up identity drift")
    for p in prompts:
        for text in ["Read-only public-source research only.", "No login, outreach, bulk download, access-control bypass",
                     "No repository edits, canonical admission or deployment.", "Stop"]:
            require(text in p["prompt"], "Follow-up scope expanded")
    headings = re.findall(r"^## (AE[0-9]{3}) (.+)$", markdown, re.MULTILINE)
    require(len(headings) == 5 and dict(headings) == {c["candidate_id"]: c["name"] for c in rows}, "Guide headings drift")
    for text in ["74", "22353", "22044", "0.723653", "0.7344", "inclusive", "strict", "retrospective",
                 "58 collections", "429 artifact", "55 candidate-by-catalog", "not an official", "Decimal",
                 "maintainer rerun", "3.278929", "confidence", "nearest", "5.2775", "58.125", "60.606",
                 "data/CC0", "source-code execution", "no universal", "rights", "mean"]:
        require(text.lower() in markdown.lower(), "Guide loses boundary: " + text)
    return {"algorithmic_efficiency_collections": 5, "unadmitted_algorithmic_efficiency_collections": 5,
            "algorithmic_efficiency_artifact_references": len(refs), "algorithmic_efficiency_qualified_findings": len(findings),
            "algorithmic_efficiency_prior_catalogs_compared": 11, "algorithmic_efficiency_overlap_comparison_cells": 55}


def check_fixtures(root):
    from read_algoperf_trial import read_trial, PINS
    root = Path(root); directory = root / "tools/evidence_program/tests/fixtures/algorithmic-efficiency"
    require({p.name for p in directory.iterdir()} == set(FIXTURE_HASHES), "Unexpected fixture payload")
    for name, expected in FIXTURE_HASHES.items():
        p = directory / name
        require(p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest() == expected,
                "Fixture/attribution drift: " + name)
    manifest = json.loads((directory / "manifest.json").read_text())
    require(manifest["license"] == "Apache-2.0" and manifest["fixture_is_cc0"] is False
            and manifest["training_data_retained"] is False and manifest["source_code_retained"] is False,
            "Fixture license/acquisition scope changed")
    for item in manifest["files"]:
        raw = (directory / item["local_name"]).read_bytes()
        require(len(raw) == item["fixture"]["bytes"] and hashlib.sha256(raw).hexdigest() == item["fixture"]["sha256"]
                and blob(raw) == item["fixture"]["git_blob_sha"], "Fixture identity mismatch")
        if item["retention"] == "exact_source_bytes":
            require(item["fixture"]["sha256"] == item["source"]["sha256"] and
                    item["fixture"]["git_blob_sha"] == item["source"]["git_blob_sha"], "Exact source identity mismatch")
        else:
            require(item["omitted_source_keys"] and item["fixture"]["sha256"] != item["source"]["sha256"],
                    "Unmarked derivative")
            require(not (set(json.loads(raw)) & set(item["omitted_source_keys"])), "Omitted field retained")
    result = read_trial(directory)
    require(result["observation_count"] == 74 and result["trial_count"] == 1
            and result["derived_result"]["row_index"] == 73
            and result["derived_result"]["comparator"] == ">=", "Trial result drift")
    return {"algorithmic_efficiency_fixture_files": len(FIXTURE_HASHES),
            "algorithmic_efficiency_observations": 74, "algorithmic_efficiency_trials": 1,
            "algorithmic_efficiency_derived_crossings": 1, "algorithmic_efficiency_official_scores": 0}

SECTIONS = {'baseline_inventory': '6d6121f1833d5b0178110c302888953dc79325fbdb3913dc6afb14023a07ed5b',
 'canonical_contract_mapping': 'bc48dd53ee5c846181e8820f89ffeb3e61057b7315f4ebd54d00bc59a0075483',
 'collector_enabled': 'fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa',
 'corrections': '74fef70d258fea0a833d4944999be24bcc43c8b645fcc57ccee091d47489dddc',
 'evidence_relationships': '71d3973ea3b31369a4b56e032f9fe8a13985f050b7d83ee6af5f74db7dd2be58',
 'focused_follow_up_prompts': '5efcefba206cdbff5f1462fb6914c44dcfa7b06ae32bac74b0a9756a18d99caf',
 'holds': '0354b0e885d7242f29829ce43fd17cd0f85b1d1788ba4196aeb6f1f89013e82a',
 'interpretation_guards': '9df8af8a47e47e0e78fe7a7211228c3bc06b065c1efa1110552033059cb7adb3',
 'inventory_relationships': 'ebf76949d65e96a28614110a0462e024e90a5ba0f54c5ff1f8c36cb4a90a372b',
 'next_actions': 'ec50c551cd26b4aa06307feccbb89fa6f29c12d397fbff3d5eb55d852b320427',
 'offline_reader': '9f3ec504281a859048965a23ccb4939e979a93e58147c7985f8a32672dad687c',
 'operational_admission': 'be10ad8a289f98500b7c9e9a132f7e40fdcc1c24d57204a3d61065c6bc142fa9',
 'original_research_baseline_commit': 'f0f7f4dde0adcd26c7885d347a4ea846cabb3471756dbae44d7c397c39f800c0',
 'priority_ranking': '6cb9bd091e51c06387e0b395379a1422100cebe7453025d45834a0a54c72c2fd',
 'ranking_basis': '5f27ea89ebd2993addb43bb636e058bad67d252dcb2bcdf5be6745559152f1a3',
 'repository_review_commit': '424f745c61c88779ed9c9fb374c9e489ab5e4ef89a3eda7704a9212170d008c0',
 'reviewed_on': '6b9df6402709e9e818c2543649efa60495b29313d05ce6e8eacc7ac607078444',
 'schema_version': 'caabdd6d7c3cbae0729256895e9d34a5abd44e62815d36f7ba1714945ec11a94',
 'smallest_testable_implementation': '7cb6ea70299314f2b97566dfbe0fcb85711de377ae8cecd2c148897d562740c6',
 'source_code_execution': 'fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa',
 'status': 'de00ea76a5609bd0461e3e27981f3803dc61b51cc3b7757da7037e8ce6d5d912',
 'strongest_limitation': '78d60388c0dbcbef58464bf6fd1e61b2156fe0bf0ca0538b07bf25443e759f9e',
 'title': '5985fdc15bf70a2bd454943277445c850262bee525a32d29c473a09f0cbe977f',
 'top_additions': '36fb48ff08686b5e7a40dd40ff004748c87c4777f14da88a6b7ed6cea8f0acb5',
 'training_data_download': 'fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa',
 'universal_efficiency_curve': 'fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa',
 'verification_separation': '69a1bb40f9e87f47a2e023afdfe1e2282e68281d48531a73ba78373da03af292'}

FAMILIES = {'AE001': '9ba43d04b2eca08a6bfe9a20637b38bf91d843797f97c413c054fee85cf6ab91',
 'AE002': 'd2a661dd769c386970f8f605a43803b176c916a8684207f9b9555d45636a62bd',
 'AE003': 'b85e3eb3495a23c448fd1a48f303882d49f2dd838585b0dc701f0ceb0d9d0f2e',
 'AE004': '9dd26ecdf0eccd51afd07e817f1c0adb56ea079049ed2318b940eb206464cc74',
 'AE005': 'b30b48b0adfa83b16a2801c58dee4fb4e040ec334cc69ac1cea9fb4d318a2e49'}

OVERLAP = '864a7acdcf2eba0194bd5cba68dfc4c06aa9d80b970dc5d3250d8e72540be832'

FIXTURE_HASHES = {'.gitattributes': '19c77e069e1c937ed8eeb2568d3dccd5e9a50d530c61589043fd16bcbf811df2',
 'LICENSE.md': '0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594',
 'NOTICE.md': '575d97bed2d8fe851b987b905604f4cb5b429b29e4cf66ff636b53a1ed3fb3ac',
 'eval_measurements.csv': 'd113215fe011f988150591f47bbc665b6f202b173ae45334d7e97f30421d0226',
 'flags_0.curated.json': '6a0aae54fbca381b336d5f86abb0cb02cacb8ff16ef4f31422eaed9c450325ec',
 'hparams.json': '3894a9524cd3f56844098f0f1fa7ecd8951f8274799ad1cdbb5aee12ade8ab00',
 'manifest.json': '1ec400ff6e7a56aeb978630ace8357e42a9ac5d81a333e840c102a36836cdbe6',
 'meta_data_0.curated.json': '43ec460c9b304d2ca480cbf08f6774f505deda982dac2ad46c864e20b66b20b1'}

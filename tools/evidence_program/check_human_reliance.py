"""Offline curated human-reliance evidence checks; no acquisition or inference."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qsl

BASE = "33fef7908a6e449c8acd38f15b8d50d65a4923a3"
IDS = {f"HR{i:03}" for i in range(1, 6)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def safe_url(value):
    require(type(value) is str and len(value) <= 2048, "Unbounded source URL")
    p = urlsplit(value)
    require(p.scheme == "https" and p.hostname and not p.username and not p.password
            and not any(c.isspace() for c in value), "Invalid source URL")
    require(not any(any(word in key.lower() for word in ["token", "secret", "credential", "signature", "api_key"])
                    for key, _ in parse_qsl(p.query)), "Private source URL")


def check_catalog(catalog, inventory_hash, markdown, root=None):
    require(type(catalog) is dict and set(catalog) == set(SECTIONS) | {"collections", "catalog_overlap_review"},
            "Reviewed catalog shape changed")
    require(catalog["repository_review_commit"] == BASE, "Wrong review base")
    require(catalog["baseline_inventory"]["sha256"] == inventory_hash, "Frozen inventory changed")
    for key, expected in SECTIONS.items():
        require(fingerprint(catalog[key]) == expected, "Reviewed section drift: " + key)
    rows = catalog["collections"]
    require(type(rows) is list and len(rows) == 5 and {x["candidate_id"] for x in rows} == IDS,
            "Five distinct experimental families required")
    require(len({x["source_family_id"] for x in rows}) == 5, "Source families merged")
    refs, findings = {}, set()
    for row in rows:
        cid = row["candidate_id"]
        require(fingerprint(row) == FAMILIES[cid], "Reviewed family semantics changed: " + cid)
        local = {x["artifact_id"] for x in row["artifacts"]}
        require(row["inventory_source_id"] is None and row["operational_admission"] == "not_admitted"
                and row["collector_enabled"] is False, "Research family improperly admitted")
        for a in row["artifacts"]:
            aid = a["artifact_id"]
            require(aid not in refs, "Duplicate artifact ID")
            refs[aid] = a
            safe_url(a["url"])
            require(a["source_bytes_vendored"] is False and a["access_status"] and a["rights_scope"],
                    "Missing access/rights/publication boundaries")
            require(a["rights_status"] in {"unknown", "declared_license"}, "Unexpected rights state")
            if a["rights_status"] == "declared_license":
                require(a["license_identifier"] and a["rights_evidence_url"], "License lacks scope/evidence")
                safe_url(a["rights_evidence_url"])
            else:
                require(a["license_identifier"] is None, "Unknown rights promoted")
            require(a["sha256"] is None, "Metadata hash converted to local exact-byte acceptance")
            for field, length in [("git_blob_sha", 40), ("git_commit", 40), ("inherited_sha256", 64),
                                  ("server_reported_sha256", 64)]:
                if a.get(field) is not None:
                    require(re.fullmatch("[a-f0-9]{" + str(length) + "}", a[field]), "Invalid source identity")
            if a.get("git_commit"):
                require("/blob/" + a["git_commit"] + "/" in a["url"], "Artifact pin/URL mismatch")
        for f in row["findings"]:
            require(f["finding_id"] not in findings and f["claim"] and f["qualification"], "Missing/duplicate finding")
            findings.add(f["finding_id"])
            require(f["evidence_artifact_ids"] and set(f["evidence_artifact_ids"]) <= local, "Broken finding source reference")
            require(f["verification_level"] in {"current_documentary_verification", "inherited_intake_not_currently_recomputed", "indexed_primary_direct_access_blocked"}, "Verification strength unknown")
    overlap = catalog["catalog_overlap_review"]
    require(set(overlap) == {"commit", "prior_collection_count", "prior_artifact_reference_count",
                            "comparison_cell_count", "catalogs_compared", "interpretation"}, "Overlap shape changed")
    require(all(type(overlap[k]) is int for k in ("prior_collection_count", "prior_artifact_reference_count", "comparison_cell_count")), "Overlap counts must be integers")
    require(overlap["commit"] == BASE and overlap["prior_collection_count"] == 53 and
            overlap["prior_artifact_reference_count"] == 404 and overlap["comparison_cell_count"] == 50,
            "Incomplete earlier-catalog comparison")
    require(overlap["interpretation"] == OVERLAP_INTERPRETATION, "Overlap uncertainty lost")
    previous = overlap["catalogs_compared"]
    require(len(previous) == 10 and {x["path"] for x in previous} == set(PRIOR), "Prior catalog missing/duplicated")
    for item in previous:
        require(fingerprint(item) == PRIOR[item["path"]], "Prior comparison identity or interpretation changed")
        require(set(item["candidate_checks"]) == IDS, "Missing candidate/catalog cell")
        if root is not None:
            raw = (Path(root) / item["path"]).read_bytes()
            require(hashlib.sha256(raw).hexdigest() == item["sha256"] and
                    hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == item["git_blob_sha"],
                    "Earlier catalog changed")
            old = json.loads(raw); oldrows = old.get("collections", old.get("families", []))
            require(len(oldrows) == item["collection_count"] and
                    sum(len(x["artifacts"]) for x in oldrows) == item["artifact_count"], "Prior counts changed")
    prompts = catalog["focused_follow_up_prompts"]
    require(len(prompts) == 6 and len({p["prompt_id"] for p in prompts}) == 6, "Prompt identities changed")
    for prompt in prompts:
        require("Read-only public-source research only." in prompt["prompt"] and
                "No login, outreach, bulk download, access-control bypass" in prompt["prompt"] and
                "No repository edits, canonical admission or deployment." in prompt["prompt"], "Follow-up authority expanded")
    headings = re.findall(r"^## (HR[0-9]{3}) (.+)$", markdown, re.MULTILINE)
    require(dict(headings) == {x["candidate_id"]: x["name"] for x in rows} and len(headings) == 5, "Guide family headings diverge")
    for phrase in ["194", "116", "1,740", "1,282", "1282", "265", "264", "508", "35%", "839", "404",
                   "50 candidate-by-catalog", "synthetic-only", "not an XLSX reader", "NoTCC", "tcc", "inherited",
                   "permission", "unknown", "absolute", "0.14", "minors", "main-regression", "static"]:
        require(phrase.lower() in markdown.lower(), "Guide loses important boundary: " + phrase)
    return {"human_reliance_collections": 5, "unadmitted_human_reliance_collections": 5,
            "human_reliance_artifact_references": len(refs), "human_reliance_qualified_findings": len(findings),
            "human_reliance_prior_catalogs_compared": 10, "human_reliance_overlap_comparison_cells": 50,
            "human_reliance_source_workbook_readers": 0, "human_reliance_participant_files_acquired": 0}


def check_aggregate_ledger(root):
    from validate_okamura_summary import validate_summary
    from decode_okamura_decisions import BIT_SCHEMA_STATUS, decode_code, summarize_synthetic
    root = Path(root)
    doc = json.loads((root / "data/evidence-program/research/okamura-aggregate-ledger.json").read_text())
    result = validate_summary(doc)
    require(result["counts"]["correct"] == 1282 and result["workbook_acceptance"] == "blocked", "Paper profile drift")
    require(BIT_SCHEMA_STATUS == "inherited_unverified_source_schema", "Synthetic map promoted")
    require(decode_code(0) is not None and decode_code(None) is None, "Zero/blank collapsed")
    bits = decode_code(19)
    require(bits["automatic_mode_raw"] is True and bits["judgment_positive_raw"] is False
            and bits["ground_truth_positive_raw"] is False and bits["overtrust_flag_raw"] is True
            and bits["tcc_flag_raw"] is True, "Inherited synthetic bit fixture changed")
    synthetic = {"schema_version": "synthetic-okamura-decisions-v1", "input_kind": "synthetic_fixture",
                 "study_id": "synthetic-okamura-task", "rows": [
                     {"row_key": 1, "group": "NoTCC", "completion_status": "complete", "checkpoints": [0, 19, 31] * 5},
                     {"row_key": 2, "group": "Visual", "completion_status": "excluded", "checkpoints": [None] * 15}]}
    out = summarize_synthetic(synthetic)
    require(out["population"] == {"recruited_rows": 2, "completer_rows": 1, "excluded_rows": 1}
            and out["author_population_counts"]["decision_count"] == 15 and
            out["excluded_rows_audit"]["missing_checkpoints"] == 15 and
            out["actual_source_acceptance"] == "blocked", "Synthetic cohort denominator drift")
    return {"human_reliance_manual_paper_count_assertions": 7, "human_reliance_manual_paper_group_assertions": 5,
            "human_reliance_synthetic_decoder_examples": 1, "human_reliance_real_workbook_acceptance_passes": 0}

SECTIONS = {'baseline_inventory': '09bd79ced01d9d20142d23fe9cd68e59418d5e8b0dc47d6b06c6128703d9693e',
 'canonical_contract_mapping': '20816d1e3195a7e9392152192e5babdd802b04fafd1867cb7f599078fade4a0e',
 'clinical_decision_tool': 'fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa',
 'collector_enabled': 'fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa',
 'corrections': 'c51144a497d307496fcf838bb94d1e71f0068f63dba199683dc18c832e0a8d9f',
 'evidence_relationships': '722bc9a9d64cff84373c078672dc0d27e36615f80eaf1ed1297acb3bad4f5821',
 'focused_follow_up_prompts': '6efe56d538b75f68807c25a778558fdec0b258f37211250e5dcbd0505abb3088',
 'holds': '610c21b5cd1704ddda066837992ccf0479be756952e9a87cf182625239a674b4',
 'interpretation_guards': '2354b9e2d11cf88e9430358db59454061b18fa57e6eb9916b46c4873232f0e22',
 'inventory_relationships': '944211d4cd2e875408c5d51cf243f400bee454eb1e8926a5c853d5b2bc1c74ef',
 'next_actions': '7b3711e836befc7cde9d02c9e7d5837587cc548b1cbd54ee51052f76292efe8d',
 'offline_work': '1f3591acb73cfdd0e0d49062cd90c274bc5c24ffcace2556dce0450db4e39281',
 'operational_admission': 'be10ad8a289f98500b7c9e9a132f7e40fdcc1c24d57204a3d61065c6bc142fa9',
 'original_research_baseline_commit': 'f0f7f4dde0adcd26c7885d347a4ea846cabb3471756dbae44d7c397c39f800c0',
 'participant_rows_acquired_current_review': 'fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa',
 'participant_rows_vendored': 'fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa',
 'priority_ranking': '6ca1836d146078e47aba09430ff23efac98a30e137bb44ed38a1a42f9dd9bc66',
 'raw_source_files_vendored': 'fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa',
 'repository_review_commit': '297a411122483d31e9167dd074a7acf8b9161d52136c8795a179905f20eed54b',
 'reviewed_on': '6b9df6402709e9e818c2543649efa60495b29313d05ce6e8eacc7ac607078444',
 'schema_version': 'a51162aeeb057ca4e3df627977231de20b581f0d0d418ca3a111bc0e408ac6cc',
 'simulator_or_model_execution': 'fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa',
 'source_code_execution': 'fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa',
 'static_source_read': 'b5bea41b6c623f7c09f1bf24dcae58ebab3c0cdd90ad966bc43a45b44867e12b',
 'static_source_read_scope': '71596d837ae038b7489d3a2e7a445575908022a9943d155c63431fdc3fd4238f',
 'status': '520cb0cedfeac692532db48ea58d712d49db3e54da3636089cafc228ab67bf91',
 'title': 'a5ea3d870ffda5815cfade6420cfce86a17db0c48e432a2583f335d43ccb70a9',
 'workbook_acquired_current_review': 'fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa'}

FAMILIES = {'HR001': 'c8858120452035474fa06596f7fcf44f0f7db5996ee9e71fe39db2589bf3f81a',
 'HR002': '87d9e049e277a074ede374e63fd80c0ab0751bf88a740e21ea1e25080700868d',
 'HR003': 'accd41c049b9ad2e746f0289a14774b832521745dd3b6966fe11995edcb8d745',
 'HR004': '9516e59c0da9eb7004110c3a9daaa5e89dee94f69b8aa8f0f9b154d1d20f541a',
 'HR005': '334ffe8ef0196497f16e1422a51d1284807aa87676abd988b0be14962738e8e2'}

PRIOR = {'data/evidence-program/research/adoption-productivity.json': '6eda113cd0aa2ec5b41f5fa6bf8e727b171bf9c5ab01331d70a0cb788a77c5e1',
 'data/evidence-program/research/chinese-safety-evaluations.json': '3a962f1080d94f4fb5e54e978b4e8d49eecf27a6709c396449cf97988b96afd3',
 'data/evidence-program/research/concentration-dependencies.json': '8d705b2b9ae83210065b176cd2f2bb6c63cf93d68ce27d7a41087a098cab37f5',
 'data/evidence-program/research/historical-capability-backfills.json': 'dfacb080d84948f4219ed76e53976709b1dd9506271eae478372a86799966e39',
 'data/evidence-program/research/open-model-diffusion.json': 'c9d694b0ab5fc4173c54d4344fcdbd1d30c965b106220d7f0a6a99023c79d574',
 'data/evidence-program/research/organizational-safety.json': '6c8f049d7626131110903f4352b32e460bdea3714de93a707a8ee3fbc893a922',
 'data/evidence-program/research/persuasion-information.json': 'ae8d7987b182dbd8d07e15721b9c1c063f9ac236adf254d7a7a21250974a5d72',
 'data/evidence-program/research/robotics-physical.json': 'c0140ce9c8dd681e111ca24f6063c17ec8f38038371889d57f207afd1360a0e9',
 'data/evidence-program/research/scientific-progress.json': 'a56d34f5e7430828a65f9d1c44e46142cc116661d67ef895cd27c5261935c48b',
 'data/evidence-program/research/training-data-feedback.json': '4489089f02653c281f7abc561cf7384b4770fa2c7fc18147fc14c97454d0ddc9'}

OVERLAP_INTERPRETATION = 'No established shared producer/study/cohort/artifact was found; absence of verified overlap does not prove participant independence. No cross-study participant linkage attempted.'

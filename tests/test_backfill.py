import json

from pdoom_pipeline.belief.appearances import speaker_blocks, speaker_turns
from pdoom_pipeline.belief.changes import view_change_candidates
from pdoom_pipeline.belief.collect import collect_beliefs
from pdoom_pipeline.export.corpus import export_corpus
from pdoom_pipeline.extract.statements import SPEAKER_GAP, extract_statements


def test_multi_sentence_probability_keeps_both_sentences_and_does_not_invent_a_quote():
    text = (
        "I think the probability is around 10%. "
        "By that I mean human extinction caused by advanced AI."
    )
    found = extract_statements(text)
    numeric = [row for row in found if row["statement_type"] == "explicit_numeric"]
    assert len(numeric) == 1
    row = numeric[0]
    assert row["question_key"] == "extinction_unconditional"
    assert row["value_numeric"] == 0.1
    assert row["value_numeric"] is not None
    assert "I think the probability is around 10%." in row["evidence_text"]
    assert "By that I mean human extinction" in row["evidence_text"]
    assert "multi_sentence_evidence" in row["review_flags"]
    assert row["review_state"] == "needs_review"
    assert row["review_state"] != "human_verified"


def test_definition_in_previous_sentence_without_anaphora_is_not_attached():
    text = "Human extinction is the outcome I worry about. I think the probability is 10%."
    found = [row for row in extract_statements(text) if row["statement_type"] == "explicit_numeric"]
    assert found == []


def test_horizon_and_condition_from_the_previous_sentence_stay_attached():
    text = (
        "Within ten years of building powerful AI. "
        "I'd put the chance that most humans die at roughly 20%."
    )
    death = [row for row in extract_statements(text) if row["question_key"] == "mass_human_death"]
    assert len(death) == 1
    assert death[0]["horizon_text"] == "within ten years"
    assert "building" in (death[0]["condition_text"] or "")
    assert "Within ten years of building powerful AI." in death[0]["evidence_text"]
    assert death[0]["question_key"] != "extinction_unconditional"
    assert "multi_sentence_evidence" in death[0]["review_flags"]


def test_unrelated_nearby_number_does_not_become_a_probability():
    text = "The model scored 90% accuracy. I think extinction is unlikely."
    found = extract_statements(text)
    assert all(row["statement_type"] != "explicit_numeric" for row in found)
    assert all(row["value_numeric"] is None for row in found)
    bait = "I think the probability is 10%. By that I mean the benchmark reached 90%, not extinction."
    assert [row for row in extract_statements(bait) if row["statement_type"] == "explicit_numeric"] == []


def test_intervening_speaker_blocks_the_window_and_unlabeled_text_is_not_a_turn():
    transcript = "\n".join(
        [
            "Ada Lovelace: I think the probability is around 10%.",
            "Host: So you mean human extinction?",
            "Ada Lovelace: By that I mean human extinction caused by advanced AI.",
        ]
    )
    turns = speaker_turns(transcript)
    blocks = speaker_blocks(turns, "Ada Lovelace")
    assert len(blocks) == 2
    joined = f"\n{SPEAKER_GAP}\n".join(block["text"] for block in blocks)
    numeric = [row for row in extract_statements(joined) if row["statement_type"] == "explicit_numeric"]
    assert numeric == []
    assert speaker_turns("I think there is a 10% chance of human extinction by 2040.") == []


def test_timestamped_speaker_labels_match_the_person_and_keep_the_other_speaker_out():
    transcript = "\n".join(
        [
            "Dario Amodei (00:01:02): I think the probability is around 10%.",
            "Dario Amodei (00:01:20): By that I mean human extinction caused by advanced AI.",
            "Dwarkesh Patel (00:01:40): The benchmark later hit 90% accuracy.",
        ]
    )
    turns = speaker_turns(transcript)
    assert [turn["speaker"] for turn in turns] == ["Dario Amodei", "Dario Amodei", "Dwarkesh Patel"]
    assert turns[0]["start_ms"] == 62_000
    blocks = speaker_blocks(turns, "Dario Amodei")
    assert len(blocks) == 1
    numeric = [row for row in extract_statements(blocks[0]["text"]) if row["question_key"] == "extinction_unconditional"]
    assert len(numeric) == 1
    assert numeric[0]["value_numeric"] == 0.1
    assert "90%" not in numeric[0]["evidence_text"]


def test_same_speaker_consecutive_turns_can_form_one_window():
    transcript = "\n".join(
        [
            "Ada Lovelace: I think the probability is around 10%.",
            "By that I mean human extinction caused by advanced AI.",
            "Host: Thanks.",
        ]
    )
    blocks = speaker_blocks(speaker_turns(transcript), "Ada Lovelace")
    assert len(blocks) == 1
    numeric = [row for row in extract_statements(blocks[0]["text"]) if row["question_key"] == "extinction_unconditional"]
    assert len(numeric) == 1
    assert numeric[0]["value_numeric"] == 0.1


def test_timeline_wording_ranges_and_relative_horizons_stay_distinct():
    before = extract_statements("I expect AGI before 2035.")
    assert before[0]["question_key"] == "agi_timeline"
    assert before[0]["horizon_text"] == "before 2035"
    assert before[0]["unit"] == "year"
    span = extract_statements("I expect ASI between 2032 and 2040.")
    assert span[0]["question_key"] == "asi_timeline"
    assert span[0]["value_type"] == "range"
    assert span[0]["value_min"] == 2032 and span[0]["value_max"] == 2040
    assert span[0]["horizon_text"] == "between 2032 and 2040"
    assert "range_value" in span[0]["review_flags"]
    relative = extract_statements("I expect transformative AI within five years.")
    assert relative[0]["question_key"] == "transformative_ai_timeline"
    assert relative[0]["horizon_text"] == "within five years"
    assert relative[0]["unit"] == "years_ahead"
    assert relative[0]["value_numeric"] == 5
    words = extract_statements("I expect human-level AI in two to three years.")
    assert words[0]["question_key"] == "human_level_ai_timeline"
    assert words[0]["value_min"] == 2 and words[0]["value_max"] == 3
    assert "two to three years" in words[0]["horizon_text"]
    decade = extract_statements("I expect AGI in the early 2030s.")
    assert decade[0]["horizon_text"] == "early 2030s"
    assert decade[0]["unit"] == "decade"
    vague = extract_statements("I expect ASI this decade.")
    assert vague[0]["forecast_kind"] == "timeline"
    assert vague[0]["statement_type"] == "explicit_qualitative"
    assert vague[0]["value_numeric"] is None
    assert vague[0]["horizon_text"] == "this decade"
    assert vague[0]["question_key"] != decade[0]["question_key"]
    assert extract_statements("We saw that pattern in the last two to three years.") == []


def test_task_share_is_not_unemployment_and_geography_is_kept():
    tasks = extract_statements("I expect 40% of tasks to be automated by 2035.")
    assert tasks[0]["question_key"] == "task_automation"
    assert tasks[0]["unit"] == "share_of_tasks_global"
    assert tasks[0]["definition_text"] == "tasks"
    assert tasks[0]["value_numeric"] == 0.4
    jobs = extract_statements("I expect 40% of jobs in the United States to be automated by 2035.")
    assert jobs[0]["question_key"] == "job_displacement"
    assert jobs[0]["unit"] == "share_of_jobs_stated-geography"
    assert "United States" in jobs[0]["definition_text"]
    assert jobs[0]["question_key"] != tasks[0]["question_key"]
    wages = extract_statements("I expect wages in Europe to rise 15% by 2035.")
    assert wages[0]["question_key"] == "wage_effect"
    assert "Europe" in wages[0]["definition_text"]
    assert wages[0]["question_key"] != jobs[0]["question_key"]


def test_duplicate_numeric_candidate_is_suppressed_and_view_changes_stay_conservative():
    text = "I think there is a 10% chance of human extinction by 2040. I think there is a 10% chance of human extinction by 2040."
    people = [{"slug": "ada-lovelace", "display_name": "Ada Lovelace", "name_distinctiveness": "high"}]
    html = f"<html><title>Ada Lovelace</title><body><p>{text}</p></body></html>"

    def fetch(url: str) -> bytes:
        if url.endswith("/robots.txt"):
            return b"User-agent: *\nDisallow:\n"
        return html.encode()

    result = collect_beliefs(
        people=people,
        leads=[{"kind": "essay", "person_slug": "ada-lovelace", "name": "Notes", "url": "https://ada.example/dup", "source_type": "blog", "basis": "byline"}],
        fetch_bytes=fetch,
        observed_at="2026-09-27T00:00:00Z",
        priority_slugs={"ada-lovelace"},
    )
    assert len(result["statements"]) == 1
    assert "possible_duplicate" in result["statements"][0]["review_flags"]
    earlier = {
        "person_id": "person:ada",
        "person_slug": "ada",
        "statement_type": "explicit_numeric",
        "question_key": "agi_timeline",
        "unit": "year",
        "value_numeric": 2035,
        "value_min": None,
        "value_max": None,
        "horizon_text": "by 2035",
        "evidence_text": "I expect AGI by 2035.",
        "published_at": "2020-01-01T00:00:00Z",
        "local_id": "early",
    }
    revised = dict(
        earlier,
        value_numeric=2032,
        evidence_text="I now think AGI by 2035 was wrong; I was wrong to say that year.",
        published_at="2024-01-01T00:00:00Z",
        local_id="later",
        horizon_text="by 2035",
    )
    # Same horizon is required. The retraction names the old horizon.
    revised["horizon_text"] = "by 2035"
    revised["evidence_text"] = "I was wrong about AGI by 2035."
    changes = view_change_candidates([earlier, revised])
    assert changes[0]["relationship_type"] == "retracts"
    assert changes[0]["review_state"] == "unreviewed"
    silent = dict(revised, evidence_text="AGI by 2032 is plausible.", value_numeric=2032, horizon_text="by 2032", local_id="other")
    assert view_change_candidates([earlier, silent]) == []


def test_same_document_revision_and_curated_byline_alias():
    earlier = {
        "person_id": "person:ajeya",
        "person_slug": "ajeya-cotra",
        "statement_type": "explicit_numeric",
        "question_key": "transformative_ai_by_year_probability",
        "unit": "probability",
        "value_numeric": 0.15,
        "value_min": None,
        "value_max": None,
        "horizon_text": "by 2036",
        "evidence_text": "Previously, my estimate was a 15% chance of transformative AI by 2036.",
        "published_at": "2022-08-01T00:00:00Z",
        "local_id": "st00001",
    }
    later = dict(
        earlier,
        value_numeric=0.35,
        evidence_text="I now expect a 35% chance of transformative AI by 2036.",
        local_id="st00002",
    )
    changes = view_change_candidates([earlier, later])
    assert changes[0]["relationship_type"] == "updates"
    assert changes[0]["review_state"] == "unreviewed"
    people = [{"slug": "joseph-carlsmith", "display_name": "Joseph Carlsmith", "name_distinctiveness": "high"}]
    html = "<html><title>Report</title><body><p>By Joe Carlsmith. I think there is a 5% chance of human extinction by 2070.</p></body></html>"

    def fetch(url: str) -> bytes:
        if url.endswith("/robots.txt"):
            return b"User-agent: *\nDisallow:\n"
        return html.encode()

    admitted = collect_beliefs(
        people=people,
        leads=[{
            "kind": "essay",
            "person_slug": "joseph-carlsmith",
            "name": "Power-seeking",
            "url": "https://joe.example/report",
            "source_type": "blog",
            "byline_alias": "Joe Carlsmith",
            "basis": "His LessWrong byline is Joe Carlsmith.",
        }],
        fetch_bytes=fetch,
        observed_at="2026-09-27T00:00:00Z",
        priority_slugs={"joseph-carlsmith"},
    )
    assert admitted["observations"]
    assert admitted["statements"][0]["question_key"] == "extinction_unconditional"
    rejected = collect_beliefs(
        people=people,
        leads=[{
            "kind": "essay",
            "person_slug": "joseph-carlsmith",
            "name": "Family only",
            "url": "https://joe.example/family",
            "source_type": "blog",
            "byline_alias": "Carlsmith",
            "basis": "family name only",
        }],
        fetch_bytes=fetch,
        observed_at="2026-09-27T00:00:00Z",
        priority_slugs={"joseph-carlsmith"},
    )
    assert rejected["observations"] == []
    assert rejected["source_leads"][0]["reason_not_admitted"] == "attribution_unresolved"


def test_body_only_name_stays_unresolved():
    people = [{"slug": "ada-lovelace", "display_name": "Ada Lovelace", "name_distinctiveness": "high"}]
    html = (
        "<html><title>Notes on machines</title><body>"
        "<p>Ada Lovelace writes that there is a 10% chance of human extinction by 2040.</p>"
        "</body></html>"
    )

    def fetch(url: str) -> bytes:
        if url.endswith("/robots.txt"):
            return b"User-agent: *\nDisallow:\n"
        return html.encode()

    result = collect_beliefs(
        people=people,
        leads=[{
            "kind": "essay",
            "person_slug": "ada-lovelace",
            "name": "Mention",
            "url": "https://notes.example/mention",
            "source_type": "blog",
            "basis": "The display name appears only in the article body.",
        }],
        fetch_bytes=fetch,
        observed_at="2026-09-27T00:00:00Z",
        priority_slugs={"ada-lovelace"},
    )
    assert result["observations"] == []
    assert result["statements"] == []
    assert result["source_leads"][0]["candidate_url"] == "https://notes.example/mention"
    assert result["source_leads"][0]["reason_not_admitted"] == "attribution_unresolved"
    assert result["source_leads"][0]["retryable"] is False


def test_candidate_leads_stay_out_of_observations_and_unspecified_is_not_a_forecast():
    people = [{"slug": "ada-lovelace", "display_name": "Ada Lovelace", "name_distinctiveness": "high"}]

    def fetch(url: str) -> bytes:
        if url.endswith("/robots.txt"):
            return b"User-agent: *\nDisallow:\n"
        if url.endswith("/talk"):
            return b"<html><title>Ada Lovelace keynote</title><body><p>Ada Lovelace expects powerful AI within five years.</p></body></html>"
        return b"<html><title>Ada Lovelace</title><body><p>Automation can be helpful.</p></body></html>"

    result = collect_beliefs(
        people=people,
        leads=[
            {
                "kind": "lead",
                "person_slug": "ada-lovelace",
                "name": "Closed",
                "url": "https://ada.example/closed",
                "source_type": "blog",
                "reason_not_admitted": "client_rendered",
                "retryable": True,
                "discovery_provenance": "personal site looked client-rendered",
            },
            {
                "kind": "talk",
                "person_slug": "ada-lovelace",
                "name": "Keynote",
                "url": "https://events.example/talk",
                "source_type": "conference_talk",
                "show_slug": "event-ada-keynote",
                "single_speaker": True,
                "basis": "Official event page lists Ada Lovelace as the only speaker.",
            },
        ],
        fetch_bytes=fetch,
        observed_at="2026-09-27T00:00:00Z",
        priority_slugs={"ada-lovelace"},
    )
    assert [row["canonical_url"] for row in result["observations"]] == ["https://events.example/talk"]
    assert result["observations"][0]["role"] == "speaker"
    assert result["observations"][0]["ownership"] == "appearance"
    assert result["source_leads"][0]["reason_not_admitted"] == "client_rendered"
    assert result["source_leads"][0]["candidate_url"] not in {row["canonical_url"] for row in result["observations"]}
    result["statements"].append(
        {
            "local_id": "qualitative-only",
            "person_slug": "ada-lovelace",
            "person_id": "person:ada-lovelace",
            "source_url": "https://events.example/talk",
            "statement_type": "explicit_qualitative",
            "forecast_kind": "qualitative",
            "question_key": None,
            "normalized_text": "Automation can be helpful in some settings.",
            "evidence_text": "Automation can be helpful in some settings.",
            "context_text": None,
            "extractor_version": "rule-extract-0.4.0",
            "confidence": "low",
            "review_state": "unreviewed",
            "topic_slug": "ai-risk-qualitative",
            "value_type": "none",
            "value_numeric": None,
            "published_at": None,
            "start_char": 0,
            "end_char": 10,
            "start_ms": None,
            "role": "speaker",
        }
    )
    document = export_corpus(result, generated_at="2026-09-27T00:00:00Z")
    assert all(row["question_key"] != "unspecified" for row in document["forecasts"])
    assert all(row["review_state"] != "human_verified" for row in document["statements"])
    assert all(row["review_state"] != "human_verified" for row in document["forecasts"])
    qualitative = [row for row in document["statements"] if row["normalized_text"].startswith("Automation can")]
    assert qualitative
    assert qualitative[0]["slug"] not in {row["statement_slug"] for row in document["forecasts"]}


def test_disempowered_is_not_extinction_and_list_continuation_keeps_the_new_number():
    text = "There is a disturbingly high risk (I think: greater than 10%) that I live to see the human species permanently and involuntarily disempowered by AI systems."
    row = extract_statements(text)[0]
    assert row["question_key"] == "disempowerment"
    assert row["definition_text"] == "disempowered"
    assert row["value_numeric"] == 0.1
    assert row["review_state"] == "needs_review"
    assert row["question_key"] != "extinction_unconditional"
    continued = extract_statements(
        "Roughly 15% probability of transformative AI by 2036. 35% probability by 2050."
    )
    numeric = [item for item in continued if item["statement_type"] == "explicit_numeric"]
    assert [item["horizon_text"] for item in numeric] == ["by 2036", "by 2050"]
    assert numeric[1]["value_numeric"] == 0.35
    assert numeric[1]["question_key"] == "transformative_ai_by_year_probability"
    assert "transformative" in numeric[1]["evidence_text"].lower()
    assert "multi_sentence_evidence" in numeric[1]["review_flags"]
    assert extract_statements("The benchmark reached 90% accuracy. 35% probability by 2050.") == []


def test_labor_replacement_keeps_tasks_jobs_and_the_next_decade_apart():
    tasks = extract_statements("We should not expect much more than about 5% of what humans do to be replaced by AI over the next decade.")
    assert tasks[0]["question_key"] == "task_automation"
    assert tasks[0]["definition_text"] == "what humans do"
    assert tasks[0]["horizon_text"] == "over the next decade"
    assert tasks[0]["review_state"] == "needs_review"
    jobs = extract_statements("In my own forecast, AI replaces about 5% of jobs over the next decade.")
    assert jobs[0]["question_key"] == "job_displacement"
    assert jobs[0]["definition_text"] == "jobs"
    assert jobs[0]["question_key"] != tasks[0]["question_key"]
    assert jobs[0]["value_numeric"] == 0.05


def test_reported_numbers_and_durations_are_not_the_speakers_forecast():
    reported = "Holden felt that it was reasonable to expect a 10% probability of transformative AI within 20 years."
    assert extract_statements(reported) == []
    duration = "It's my guess that powerful AI could give us the next 50-100 years of biological progress in 5-10 years."
    rows = [row for row in extract_statements(duration) if row["statement_type"] == "explicit_numeric"]
    assert len(rows) == 1
    assert rows[0]["value_min"] == 5 and rows[0]["value_max"] == 10
    assert "50" not in (rows[0]["horizon_text"] or "")
    slider = "I think you don't want to set it at 100%, because there might be some tail tasks that take a long time to automate."
    assert extract_statements(slider) == []
    scenario = "The 2030s in our scenario are the decade of top-human-level AI."
    assert extract_statements(scenario) == []


def test_for_that_uses_the_previous_outcome_and_a_misreading_does_not():
    text = (
        "Do I expect this race to play a central causal role in the extinction of humanity? "
        "I'll give a probability of around 2% for that."
    )
    row = [item for item in extract_statements(text) if item["statement_type"] == "explicit_numeric"][0]
    assert row["question_key"] == "extinction_unconditional"
    assert row["value_numeric"] == 0.02
    assert "extinction of humanity" in row["evidence_text"]
    assert "multi_sentence_evidence" in row["review_flags"]
    assert row["review_state"] == "needs_review"
    misread = "Some people interpreted this to mean that I estimated the probability of AI causing an existential catastrophe at somewhere around 2%."
    assert extract_statements(misread) == []
    other_cause = "Even before AI, I assigned a way higher than 2% probability to existential catastrophe caused by nuclear war."
    assert extract_statements(other_cause) == []


def test_another_persons_timeline_is_not_extracted_and_a_median_is():
    assert extract_statements('Dario Amodei thinks there might be only 2 to 3 years left until AI surpasses almost all humans.') == []
    row = extract_statements("Compared with others, my own median timelines of ~ 20 years until full automation of remote work would be considered aggressive.")[0]
    assert row["question_key"] == "remote_work_automation"
    assert row["value_numeric"] == 20
    assert row["unit"] == "years_ahead"
    assert row["definition_text"] == "full automation of remote work"
    assert "20 years" in row["horizon_text"]
    assert row["question_key"] != "agi_timeline"
    assert row["review_state"] == "needs_review"
    plausible = extract_statements("I still think full automation of remote work in 10 years is plausible.")[0]
    assert plausible["statement_type"] == "explicit_qualitative"
    assert plausible["question_key"] == "remote_work_automation"
    assert plausible["horizon_text"] == "in 10 years"
    assert plausible["value_numeric"] is None
    assert plausible["review_state"] == "unreviewed"


def test_relative_time_without_a_topic_is_not_a_forecast():
    life = "It feels very likely in 50 years that the average American's day to day life looks very similar."
    assert extract_statements(life) == []
    aside = "I said it's plausible that could happen in two years with minor human oversight."
    assert extract_statements(aside) == []


def test_historical_observation_and_deployment_policy_are_not_forecasts():
    past = "I think you have to look at the things that we've invented so far and notice that none of them really had any plausible mechanism of causing extinction."
    assert extract_statements(past) == []
    policy = "Deploying AI systems only when they are unlikely to cause a catastrophe is the cautious path."
    assert extract_statements(policy) == []


def test_identical_later_forecast_is_a_repeat_and_a_silent_number_change_is_not():
    earlier = {
        "person_id": "person:holden",
        "statement_type": "explicit_numeric",
        "question_key": "transformative_ai_by_year_probability",
        "unit": "probability",
        "value_numeric": 0.1,
        "value_min": None,
        "value_max": None,
        "horizon_text": "by 2036",
        "evidence_text": "I believe there's more than a 10% chance of transformative AI by 2036.",
        "published_at": "2021-08-24T00:00:00Z",
        "local_id": "st00001",
    }
    later = dict(
        earlier,
        evidence_text="I estimate that there is more than a 10% chance we'll see transformative AI by 2036.",
        published_at="2021-09-07T00:00:00Z",
        local_id="st00002",
    )
    changes = view_change_candidates([earlier, later])
    assert changes[0]["relationship_type"] == "repeats"
    assert changes[0]["review_state"] == "unreviewed"
    changed = dict(later, value_numeric=0.2, evidence_text="I estimate a 20% chance of transformative AI by 2036.")
    assert view_change_candidates([earlier, changed]) == []


def test_source_registration_collapses_canonical_url_duplicates(tmp_path):
    from pdoom_pipeline.jobs.collect_beliefs import _register_sources

    seed = tmp_path
    (seed / "sources.jsonl").write_text("", encoding="utf-8")
    lead = {
        "kind": "essay",
        "person_slug": "ada-lovelace",
        "name": "Notes",
        "url": "https://ada.example/notes/",
        "source_type": "blog",
        "basis": "Her page.",
    }
    _register_sources(seed, [lead], {"observations": []})
    _register_sources(seed, [lead], {"observations": []})
    rows = [json.loads(line) for line in (seed / "sources.jsonl").read_text().splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["canonical_url"] == "https://ada.example/notes"

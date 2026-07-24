import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from worker_runtime.disambiguation import run_disambiguation
from worker_runtime.errors import OutputValidationError
from worker_runtime.providers import DeepSeekChatCompletionsProvider, FixtureProvider, LLMProvider, OpenAIResponsesProvider, parse_json_object
from worker_runtime.research import build_draft_instructions, normalize_source_quality, run_confirmed_research


def request() -> dict:
    return {
        "job_id": "job_test_villa_savoye",
        "idempotency_key": "test-key",
        "mode": "generate",
        "requested_by": {"user_id": "test", "role": "editor"},
        "project": {"query": "Villa Savoye, Le Corbusier, Poissy"},
        "research_options": {},
        "requested_at": "2026-07-23T10:00:00Z",
    }


class InvalidProvider(LLMProvider):
    def disambiguate(self, *, instructions, request, schema):
        return {"job_id": request["job_id"], "status": "not-a-real-status"}


class DisambiguationRuntimeTests(unittest.TestCase):
    def test_fixture_provider_writes_schema_valid_result(self):
        with tempfile.TemporaryDirectory() as directory:
            output = run_disambiguation(request=request(), jobs_root=Path(directory), provider=FixtureProvider())
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "identity_confirmed")
            self.assertEqual(result["candidates"][0]["candidate_id"], "villa-savoye-1931")

    def test_invalid_provider_records_schema_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(OutputValidationError):
                run_disambiguation(request=request(), jobs_root=Path(directory), provider=InvalidProvider())
            events = (Path(directory) / "job_test_villa_savoye" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"state": "failed"', events)

    def test_confirmed_candidate_generates_and_validates_private_draft(self):
        source_url = "https://example.org/captains-house"

        class DraftProvider(FixtureProvider):
            def generate_case_draft(self, *, instructions, request, confirmation, research_results, schema):
                source = research_results[0]
                source_id = "s1"
                strategy = {
                    "strategy_name": "保留并重组既有空间",
                    "design_problem": "既有住宅需要在改造中保持可居住性。",
                    "specific_approach": "以确认后的资料为基础梳理空间和视线。",
                    "architectural_effect": "形成更清晰的日常使用秩序。",
                    "evidence": "Directly sourced",
                    "source_ids": [source_id],
                    "related_image_ids": [],
                    "transferable_lesson": "先确认既有条件，再决定介入范围。",
                }
                case_json = {
                    "project_name": "Villa Savoye",
                    "source_mode": "web",
                    "architects": ["Le Corbusier", "Pierre Jeanneret"],
                    "location": "Poissy, France",
                    "year": "1931",
                    "program": "House",
                    "status": "built",
                    "case_type": "housing",
                    "disambiguation_status": "confirmed",
                    "disambiguation_candidates": [{
                        "candidate_project": "Villa Savoye",
                        "location": "Poissy, France",
                        "architects": "Le Corbusier and Pierre Jeanneret",
                        "year": "1931",
                        "type": "housing",
                        "main_sources": [source_url],
                        "confidence": "high",
                        "question_for_user": "Confirmed by editor.",
                    }],
                    "information_confidence": "limited",
                    "incomplete_reason": "This minimal worker draft has no reliable image research yet; image handling remains pending.",
                    "one_sentence_summary": "以已确认来源形成的最小案例草稿。",
                    "key_facts": [{"label": "Project", "value": "Villa Savoye", "source_ids": [source_id]}],
                    "design_concept": {
                        "sourced_concept": "The retrieved source identifies the confirmed project.",
                        "ai_synthesis": "The draft is deliberately limited to the retrieved material.",
                        "source_ids": [source_id],
                    },
                    "key_strategies": [strategy, {**strategy, "strategy_name": "控制事实边界"}, {**strategy, "strategy_name": "保留待核验项"}],
                    "spatial_ideas": [],
                    "materials_structure": [],
                    "site_context": [],
                    "image_metadata": [],
                    "download_mode": "requested",
                    "source_quality": {
                        "has_primary_sources": False,
                        "primary_sources_used_for_identity": False,
                        "architecture_media_count": 1,
                        "wechat_valid_result_count": 0,
                        "zhihu_valid_result_count": 0,
                        "source_sufficiency_status": "insufficient",
                        "secondary_source_heavy": True,
                        "manual_review_needed": ["Expand source collection and image research before publication."],
                        "identity_confirming_source_ids": [source_id],
                        "analysis_coverage": ["concept", "program", "circulation"],
                    },
                    "sources": [{
                        "id": source_id,
                        "title": source["title"],
                        "url": source["url"],
                        "source_level": "level_b",
                        "publisher": "Example Architecture",
                        "accessed_date": "2026-07-23",
                        "notes": "Retrieved by the controlled test search.",
                    }],
                    "uncertain_or_conflicting_info": [{
                        "topic": "Images",
                        "description": "No reliable image has been researched in this minimal stage.",
                        "source_ids": [source_id],
                    }],
                }
                return {
                    "case_json": case_json,
                    "case_md": f"# Villa Savoye\n\n最小草稿，仅基于已检索来源。\n\n## 来源\n\n- [{source['title']}]({source['url']})\n",
                }

        research_results = [{
            "rank": 1,
            "title": "Example source",
            "url": source_url,
            "snippet": "A confirmed source.",
            "page_excerpt": "A confirmed source about the project.",
            "retrieved_at": "2026-07-23T10:00:00Z",
        }]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_disambiguation(request=request(), jobs_root=root, provider=FixtureProvider())
            with patch("worker_runtime.research.collect_research_results", return_value=research_results):
                output = run_confirmed_research(
                    request=request(),
                    jobs_root=root,
                    provider=DraftProvider(),
                    confirmation={
                        "job_id": "job_test_villa_savoye",
                        "candidate_id": "villa-savoye-1931",
                        "confirmed_by": {"user_id": "editor", "role": "editor"},
                        "confirmed_at": "2026-07-23T10:02:00Z",
                    },
                )
            self.assertTrue((output / "case.json").exists())
            validation = json.loads((root / "job_test_villa_savoye" / "artifacts" / "validation.json").read_text(encoding="utf-8"))
            self.assertEqual(validation["validator"]["exit_code"], 0)
            self.assertIn("quality", validation)
            events = (root / "job_test_villa_savoye" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"state": "awaiting_review"', events)

    def test_confirmation_rejects_candidate_not_emitted_by_job(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_disambiguation(request=request(), jobs_root=root, provider=FixtureProvider())
            with self.assertRaises(OutputValidationError):
                run_confirmed_research(
                    request=request(),
                    jobs_root=root,
                    provider=FixtureProvider(),
                    confirmation={
                        "job_id": "job_test_villa_savoye",
                        "candidate_id": "not-emitted",
                        "confirmed_by": {"user_id": "editor", "role": "editor"},
                        "confirmed_at": "2026-07-23T10:02:00Z",
                    },
                )

    def test_source_sufficiency_is_downgraded_when_confirmation_evidence_is_missing(self):
        case_json = {
            "information_confidence": "high",
            "source_quality": {
                "source_sufficiency_status": "sufficient",
                "identity_confirming_source_ids": ["official-project-page"],
                "manual_review_needed": [],
            },
        }

        normalize_source_quality(case_json)

        self.assertEqual(case_json["source_quality"]["source_sufficiency_status"], "partial")
        self.assertEqual(case_json["information_confidence"], "medium")
        self.assertTrue(case_json["source_quality"]["manual_review_needed"])

    def test_full_research_prompt_includes_skill_references(self):
        instructions = build_draft_instructions()
        self.assertIn("Full-research reference: source-quality.md", instructions)
        self.assertIn("Architectural Language Generation", instructions)

    def test_openai_client_sends_strict_schema_without_network(self):
        schema = {"type": "object", "additionalProperties": False, "properties": {}, "required": []}
        response = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"ok": true}'}],
                }
            ]
        }

        class FakeResponse:
            def read(self):
                return json.dumps(response).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch("worker_runtime.providers.urlopen", return_value=FakeResponse()) as request_call:
            provider = OpenAIResponsesProvider(api_key="test-key", model="model-under-test")
            result = provider.disambiguate(instructions="test", request=request(), schema=schema)

        payload = json.loads(request_call.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(result, {"ok": True})
        self.assertFalse(payload["store"])
        self.assertEqual(payload["model"], "model-under-test")
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertEqual(payload["text"]["format"]["schema"], schema)

    def test_deepseek_client_requests_json_mode_without_network(self):
        schema = {"type": "object", "additionalProperties": False, "properties": {}, "required": []}
        response = {"choices": [{"finish_reason": "stop", "message": {"content": '{"ok": true}'}}]}

        class FakeResponse:
            def read(self):
                return json.dumps(response).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch("worker_runtime.providers.urlopen", return_value=FakeResponse()) as request_call:
            provider = DeepSeekChatCompletionsProvider(api_key="test-key", model="model-under-test")
            result = provider.disambiguate(instructions="test instructions", request=request(), schema=schema)

        http_request = request_call.call_args.args[0]
        payload = json.loads(http_request.data.decode("utf-8"))
        self.assertEqual(result, {"ok": True})
        self.assertEqual(http_request.full_url, "https://api.deepseek.com/chat/completions")
        self.assertEqual(payload["model"], "model-under-test")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertIn("JSON Schema", payload["messages"][0]["content"])
        self.assertEqual(json.loads(payload["messages"][1]["content"]), request())

    def test_deepseek_case_draft_request_includes_research_context(self):
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"case_json": {"type": "object"}, "case_md": {"type": "string"}},
            "required": ["case_json", "case_md"],
        }
        response = {"choices": [{"finish_reason": "stop", "message": {"content": '{"case_json": {}, "case_md": "# Draft"}'}}]}

        class FakeResponse:
            def read(self):
                return json.dumps(response).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch("worker_runtime.providers.urlopen", return_value=FakeResponse()) as request_call:
            provider = DeepSeekChatCompletionsProvider(api_key="test-key", model="model-under-test", max_tokens=4321)
            result = provider.generate_case_draft(
                instructions="draft instructions",
                request=request(),
                confirmation={"job_id": request()["job_id"], "candidate_id": "candidate-1"},
                research_results=[{"title": "Source", "url": "https://example.org/source", "page_excerpt": "Evidence"}],
                schema=schema,
            )

        payload = json.loads(request_call.call_args.args[0].data.decode("utf-8"))
        context = json.loads(payload["messages"][1]["content"])
        self.assertEqual(result, {"case_json": {}, "case_md": "# Draft"})
        self.assertEqual(payload["max_tokens"], 4321)
        self.assertEqual(context["confirmation"]["candidate_id"], "candidate-1")
        self.assertEqual(context["research_results"][0]["url"], "https://example.org/source")

    def test_deepseek_json_parser_accepts_accidental_markdown_fence(self):
        self.assertEqual(
            parse_json_object("```json\n{\"ok\": true}\n```", provider_name="test provider"),
            {"ok": True},
        )

    def test_deepseek_json_parser_repairs_literal_newline_inside_string(self):
        self.assertEqual(
            parse_json_object('{"case_md":"# Draft\nBody"}', provider_name="test provider"),
            {"case_md": "# Draft\nBody"},
        )


if __name__ == "__main__":
    unittest.main()

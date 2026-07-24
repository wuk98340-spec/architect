"""LLM provider boundary. Keep vendor HTTP calls out of worker pipeline code."""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import ProviderConfigurationError, ProviderRequestError, ProviderResponseFormatError


class LLMProvider(ABC):
    @abstractmethod
    def disambiguate(self, *, instructions: str, request: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        """Return one JSON object matching the supplied disambiguation schema."""

    def generate_case_draft(
        self,
        *,
        instructions: str,
        request: dict[str, Any],
        confirmation: dict[str, Any],
        research_results: list[dict[str, Any]],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a structured case-package draft from retrieved source material."""
        raise ProviderRequestError(f"{type(self).__name__} does not implement case-draft generation.")


@dataclass(frozen=True)
class OpenAIResponsesProvider(LLMProvider):
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: int = 90

    @classmethod
    def from_environment(cls) -> "OpenAIResponsesProvider":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ProviderConfigurationError("OPENAI_API_KEY is required when ARCHITECT_LLM_PROVIDER=openai.")
        return cls(
            api_key=api_key,
            model=os.environ.get("ARCHITECT_LLM_MODEL", "gpt-5.6").strip() or "gpt-5.6",
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            timeout_seconds=int(os.environ.get("ARCHITECT_LLM_TIMEOUT_SECONDS", "90")),
        )

    def disambiguate(self, *, instructions: str, request: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        return self._request_json(instructions=instructions, input_value=request, schema=schema, schema_name="disambiguation_result")

    def generate_case_draft(
        self,
        *,
        instructions: str,
        request: dict[str, Any],
        confirmation: dict[str, Any],
        research_results: list[dict[str, Any]],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request_json(
            instructions=instructions,
            input_value={
                "generation_request": request,
                "confirmation": confirmation,
                "research_results": research_results,
            },
            schema=schema,
            schema_name="case_draft_result",
        )

    def _request_json(self, *, instructions: str, input_value: dict[str, Any], schema: dict[str, Any], schema_name: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "store": False,
            "instructions": instructions,
            "input": json.dumps(input_value, ensure_ascii=False),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = Request(
            f"{self.base_url}/responses",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=self.timeout_seconds) as response:
                raw_response = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:1000]
            raise ProviderRequestError(f"OpenAI Responses API returned HTTP {error.code}: {detail}") from error
        except URLError as error:
            raise ProviderRequestError(f"OpenAI Responses API network error: {error.reason}") from error
        except TimeoutError as error:
            raise ProviderRequestError("OpenAI Responses API request timed out.") from error
        except json.JSONDecodeError as error:
            raise ProviderRequestError("OpenAI Responses API returned invalid JSON.") from error

        text = extract_response_text(raw_response)
        try:
            result = json.loads(text)
        except json.JSONDecodeError as error:
            raise ProviderRequestError("OpenAI Responses API returned non-JSON structured output.") from error
        if not isinstance(result, dict):
            raise ProviderRequestError("OpenAI Responses API structured output must be a JSON object.")
        return result


@dataclass(frozen=True)
class DeepSeekChatCompletionsProvider(LLMProvider):
    """DeepSeek's OpenAI-compatible Chat Completions adapter.

    DeepSeek JSON mode guarantees valid JSON syntax but not a full JSON Schema
    match. The disambiguation stage therefore keeps its existing local schema
    validation as the authoritative contract gate.
    """

    api_key: str
    model: str
    base_url: str = "https://api.deepseek.com"
    timeout_seconds: int = 90
    max_tokens: int = 16000

    @classmethod
    def from_environment(cls) -> "DeepSeekChatCompletionsProvider":
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise ProviderConfigurationError("DEEPSEEK_API_KEY is required when ARCHITECT_LLM_PROVIDER=deepseek.")
        return cls(
            api_key=api_key,
            model=os.environ.get("ARCHITECT_LLM_MODEL", "deepseek-v4-flash").strip() or "deepseek-v4-flash",
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            timeout_seconds=int(os.environ.get("ARCHITECT_LLM_TIMEOUT_SECONDS", "90")),
            max_tokens=int(os.environ.get("ARCHITECT_LLM_MAX_TOKENS", "16000")),
        )

    def disambiguate(self, *, instructions: str, request: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        return self._request_json(instructions=instructions, input_value=request, schema=schema)

    def generate_case_draft(
        self,
        *,
        instructions: str,
        request: dict[str, Any],
        confirmation: dict[str, Any],
        research_results: list[dict[str, Any]],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request_json(
            instructions=instructions,
            input_value={
                "generation_request": request,
                "confirmation": confirmation,
                "research_results": research_results,
            },
            schema=schema,
        )

    def _request_json(self, *, instructions: str, input_value: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        schema_text = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{instructions}\n\n"
                        "JSON response requirement: return one JSON object only, with no Markdown or commentary. "
                        "It must match this JSON Schema exactly; the worker will validate it after this response:\n"
                        f"{schema_text}"
                    ),
                },
                {"role": "user", "content": json.dumps(input_value, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
            "stream": False,
            "max_tokens": self.max_tokens,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=self.timeout_seconds) as response:
                raw_response = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:1000]
            raise ProviderRequestError(f"DeepSeek Chat Completions API returned HTTP {error.code}: {detail}") from error
        except URLError as error:
            raise ProviderRequestError(f"DeepSeek Chat Completions API network error: {error.reason}") from error
        except TimeoutError as error:
            raise ProviderRequestError("DeepSeek Chat Completions API request timed out.") from error
        except json.JSONDecodeError as error:
            raise ProviderRequestError("DeepSeek Chat Completions API returned invalid JSON.") from error

        text, finish_reason = extract_chat_completion_text(raw_response)
        result = parse_json_object(
            text,
            provider_name="DeepSeek Chat Completions API",
            finish_reason=finish_reason,
        )
        if not isinstance(result, dict):
            raise ProviderRequestError("DeepSeek Chat Completions API JSON output must be a JSON object.")
        return result


@dataclass(frozen=True)
class FixtureProvider(LLMProvider):
    """Deterministic offline provider used only for local contract testing."""

    def disambiguate(self, *, instructions: str, request: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        project = request.get("project", {})
        query = str(project.get("query") or "").lower()
        if "villa savoye" in query:
            candidate = {
                "candidate_id": "villa-savoye-1931",
                "project_name": "Villa Savoye",
                "location": "Poissy, France",
                "architect_or_studio": "Le Corbusier and Pierre Jeanneret",
                "year": "1931",
                "case_type": "housing",
                "source_urls": [],
                "confidence": "high",
            }
            question = "请确认是否研究法国普瓦西的 Villa Savoye（1931）。"
            status = "identity_confirmed"
        else:
            candidate = {
                "candidate_id": "candidate-1",
                "project_name": str(project.get("query") or "Unknown project"),
                "location": str(project.get("location_hint") or "Unknown"),
                "architect_or_studio": str(project.get("architect_or_studio") or "Unknown"),
                "year": str(project.get("year_hint") or "Unknown"),
                "case_type": str(project.get("case_type_hint") or "other"),
                "source_urls": [],
                "confidence": "low",
            }
            question = "项目身份尚未确认，请在接入真实 LLM 与检索能力后复核。"
            status = "confirmation_required"
        return {
            "job_id": request["job_id"],
            "status": status,
            "candidates": [candidate],
            "confirmation_question": question,
            "created_at": "1970-01-01T00:00:00Z",
        }


def create_provider(name: str | None = None) -> LLMProvider:
    provider_name = (name or os.environ.get("ARCHITECT_LLM_PROVIDER", "openai")).strip().lower()
    if provider_name == "openai":
        return OpenAIResponsesProvider.from_environment()
    if provider_name == "deepseek":
        return DeepSeekChatCompletionsProvider.from_environment()
    if provider_name == "fixture":
        return FixtureProvider()
    raise ProviderConfigurationError(
        f"Unsupported ARCHITECT_LLM_PROVIDER={provider_name!r}. Supported values: openai, deepseek, fixture."
    )


def extract_response_text(response: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in response.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    if parts:
        return "".join(parts)
    raise ProviderRequestError("OpenAI Responses API response did not contain output_text.")


def extract_chat_completion_text(response: dict[str, Any]) -> tuple[str, str | None]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderRequestError("DeepSeek Chat Completions API response did not contain choices.")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ProviderRequestError("DeepSeek Chat Completions API returned an invalid choice.")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise ProviderRequestError("DeepSeek Chat Completions API response did not contain a message.")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        finish_reason = first_choice.get("finish_reason")
        suffix = f" (finish_reason={finish_reason!r})" if finish_reason else ""
        raise ProviderRequestError(f"DeepSeek Chat Completions API returned empty JSON content{suffix}.")
    finish_reason = first_choice.get("finish_reason")
    return content, str(finish_reason) if finish_reason is not None else None


def parse_json_object(
    text: str, *, provider_name: str, finish_reason: str | None = None
) -> dict[str, Any]:
    """Parse JSON mode output while tolerating an accidental Markdown fence.

    Schema validation remains mandatory in the worker stage after this boundary,
    so accepting a fenced JSON object never weakens the package contract.
    """
    candidates = [text.strip()]
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text.strip(), flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1).strip())
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        candidates.append(text[first_brace : last_brace + 1])
    candidates.extend(_escape_literal_control_characters(candidate) for candidate in list(candidates))

    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    preview = re.sub(r"\s+", " ", text).strip()[:240]
    raise ProviderResponseFormatError(
        f"{provider_name} returned non-JSON output. Preview: {preview!r}",
        provider_name=provider_name,
        content=text,
        finish_reason=finish_reason,
    )


def _escape_literal_control_characters(value: str) -> str:
    """Repair literal newlines/tabs inside a JSON string, if a model emits them.

    JSON permits these characters only as escapes. This conservative repair does
    not add, remove, or alter JSON fields; the caller still validates the full
    object against the required schema.
    """
    repaired: list[str] = []
    inside_string = False
    escaped = False
    for character in value:
        if inside_string and character in {"\n", "\r", "\t"}:
            repaired.append(json.dumps(character)[1:-1])
            escaped = False
            continue
        repaired.append(character)
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == '"':
            inside_string = not inside_string
    return "".join(repaired)

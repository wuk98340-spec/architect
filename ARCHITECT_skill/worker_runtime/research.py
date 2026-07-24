"""Confirmed-candidate research, private draft generation, and package validation."""

from __future__ import annotations

import json
import importlib.util
import re
import shutil
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse, urlunparse
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .disambiguation import (
    RUNTIME_ROOT,
    SKILL_ROOT,
    append_event,
    read_json,
    validate_generation_request,
    write_json,
)
from .errors import OutputValidationError, ProviderRequestError, ProviderResponseFormatError
from .providers import LLMProvider


TEMPLATE_ROOT = SKILL_ROOT / "worker-templates"
CASE_SCHEMA_PATH = SKILL_ROOT / "references" / "case-package-schema.json"
DRAFT_SCHEMA_PATH = RUNTIME_ROOT / "schemas" / "case-draft-result.schema.json"
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "validate_case_package.py"
QUALITY_REVIEWER_PATH = RUNTIME_ROOT.parent / "scripts" / "review_case_quality.py"
WORKSPACE_ROOT = RUNTIME_ROOT.parent.parent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36"
IMAGE_PIPELINE_PATH = RUNTIME_ROOT.parent / "scripts" / "image_pipeline.py"
SOURCE_LEVELS = {
    "official": "level_a", "architect": "level_a", "archdaily": "level_b",
    "gooood": "level_b", "archiposition": "level_b", "youfang": "level_b",
    "weixin": "level_c", "zhihu": "level_c",
}


class _DuckDuckGoParser(HTMLParser):
    """Small parser for the stable HTML search result markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture_title = False
        self._capture_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class", "") or ""
        if tag == "a" and "result__a" in classes:
            self._current = {"title": "", "url": self._decode_result_url(attributes.get("href", "")), "snippet": ""}
            self._capture_title = True
        elif tag in {"a", "div"} and "result__snippet" in classes and self._current is not None:
            self._capture_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture_title:
            self._capture_title = False
            if self._current and self._current["url"]:
                self.results.append(self._current)
            self._current = None
        elif tag in {"a", "div"}:
            self._capture_snippet = False

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._capture_title:
            self._current["title"] = f"{self._current['title']} {text}".strip()
        elif self._capture_snippet:
            self._current["snippet"] = f"{self._current['snippet']} {text}".strip()

    @staticmethod
    def _decode_result_url(value: str) -> str:
        if not value:
            return ""
        parsed = urlparse(value)
        encoded = parse_qs(parsed.query).get("uddg", [""])[0]
        return encoded or value


class _BingParser(HTMLParser):
    """Extract ordinary Bing result cards without depending on a CSS library."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._stack: list[str] = []
        self._current: dict[str, str] | None = None
        self._result_stack_depth = 0
        self._inside_h2 = False
        self._capture_title = False
        self._capture_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        self._stack.append(tag)
        classes = attributes.get("class", "") or ""
        if tag == "li" and "b_algo" in classes:
            self._current = {"title": "", "url": "", "snippet": ""}
            self._result_stack_depth = len(self._stack)
            return
        if self._current is None:
            return
        if tag == "h2":
            self._inside_h2 = True
        elif tag == "a" and self._inside_h2 and attributes.get("href"):
            self._current["url"] = attributes["href"] or ""
            self._capture_title = True
        elif tag == "p":
            self._capture_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if self._current is not None:
            if tag == "a":
                self._capture_title = False
            elif tag == "h2":
                self._inside_h2 = False
            elif tag == "p":
                self._capture_snippet = False
            elif tag == "li" and len(self._stack) == self._result_stack_depth:
                if self._current["url"]:
                    self.results.append(self._current)
                self._current = None
                self._result_stack_depth = 0
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._capture_title:
            self._current["title"] = f"{self._current['title']} {text}".strip()
        elif self._capture_snippet:
            self._current["snippet"] = f"{self._current['snippet']} {text}".strip()


class _YahooParser(HTMLParser):
    """Extract organic Yahoo result cards, including their safe redirect URLs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._stack: list[str] = []
        self._current: dict[str, str] | None = None
        self._result_stack_depth = 0
        self._inside_h3 = False
        self._capture_title = False
        self._capture_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        self._stack.append(tag)
        classes = attributes.get("class", "") or ""
        if tag == "div" and "algo" in classes.split():
            self._current = {"title": "", "url": "", "snippet": ""}
            self._result_stack_depth = len(self._stack)
            return
        if self._current is None:
            return
        if tag == "a" and not self._current["url"] and attributes.get("href"):
            self._current["url"] = self._decode_result_url(attributes["href"] or "")
        elif tag == "h3":
            self._inside_h3 = True
            self._capture_title = bool(self._current["url"])
        elif tag == "p":
            self._capture_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if self._current is not None:
            if tag == "h3":
                self._inside_h3 = False
                self._capture_title = False
            elif tag == "p":
                self._capture_snippet = False
            elif tag == "div" and len(self._stack) == self._result_stack_depth:
                if self._current["url"]:
                    self.results.append(self._current)
                self._current = None
                self._result_stack_depth = 0
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._capture_title:
            self._current["title"] = f"{self._current['title']} {text}".strip()
        elif self._capture_snippet:
            self._current["snippet"] = f"{self._current['snippet']} {text}".strip()

    @staticmethod
    def _decode_result_url(value: str) -> str:
        match = re.search(r"/RU=([^/]+)/", value)
        return unquote(match.group(1)) if match else value


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def run_confirmed_research(
    *,
    request: dict[str, Any],
    jobs_root: Path,
    provider: LLMProvider,
    confirmation: dict[str, Any],
) -> Path:
    """Generate and validate a draft only after a stored candidate is confirmed."""
    validate_generation_request(request)
    job_id = str(request["job_id"])
    workspace = jobs_root / job_id
    artifact_dir = workspace / "artifacts"
    disambiguation_path = artifact_dir / "disambiguation.json"
    if not disambiguation_path.exists():
        raise OutputValidationError("cannot confirm a job without artifacts/disambiguation.json.")

    stored_request = read_json(workspace / "request.json")
    if stored_request.get("job_id") != job_id:
        raise OutputValidationError("stored request job_id does not match the confirmed job.")
    result = read_json(disambiguation_path)
    candidate = validate_confirmation(confirmation=confirmation, job_id=job_id, disambiguation=result)
    write_json(workspace / "confirmation.json", confirmation)
    append_event(workspace, job_id, "generating", "candidate_confirmed", "编辑已确认候选，开始最小研究阶段。")

    try:
        pdf_sources = collect_pdf_sources(request=request, workspace=workspace)
        research_results = collect_research_results(request=request, candidate=candidate)
        provider_research_results = [*pdf_sources, *research_results]
        if not provider_research_results:
            raise ProviderRequestError("web retrieval returned no usable sources; draft generation was not started.")
        image_candidates = collect_image_candidates(
            research_results=research_results,
            image_root=artifact_dir / "image-research",
            enabled=str((request.get("research_options") or {}).get("image_mode", "")) == "research_download",
        )
        if image_candidates:
            provider_research_results.append({"kind": "image_research", "candidates": image_candidates})
        write_json(
            artifact_dir / "research-results.json",
            {"queries": build_source_queries(request, candidate), "results": research_results, "pdf_sources": pdf_sources, "image_candidates": image_candidates},
        )

        case_schema = read_json(CASE_SCHEMA_PATH)
        result_schema = read_json(DRAFT_SCHEMA_PATH)
        provider_schema = build_provider_draft_schema(result_schema=result_schema, case_schema=case_schema)
        instructions = build_draft_instructions()
        draft = provider.generate_case_draft(
            instructions=instructions,
            request=stored_request,
            confirmation=confirmation,
            research_results=provider_research_results,
            schema=provider_schema,
        )
        validate_draft_result(draft, result_schema=result_schema, case_schema=case_schema)
        validate_retrieved_source_urls(draft["case_json"], research_results, pdf_sources)
        validate_image_candidates(case_json=draft["case_json"], candidates=image_candidates)
        normalize_source_quality(draft["case_json"])

        package_slug = make_package_slug(str(candidate["candidate_id"]))
        package_dir = artifact_dir / "package" / package_slug
        write_json(package_dir / "case.json", draft["case_json"])
        (package_dir / "case.md").write_text(
            ensure_selected_images_embedded(draft["case_md"], draft["case_json"]), encoding="utf-8"
        )
        materialize_pdf_sources(package_dir=package_dir, sources=pdf_sources)
        materialize_selected_images(package_dir=package_dir, candidates=image_candidates, case_json=draft["case_json"])

        append_event(workspace, job_id, "validating", "stage_started", "案例草稿已生成，正在运行现有 case.json / case.md 校验。")
        validation = run_package_validation(job_id=job_id, package_slug=package_slug, package_dir=package_dir)
        write_json(artifact_dir / "validation.json", validation)
        if isinstance(validation.get("quality"), dict):
            write_json(artifact_dir / "quality-report.json", validation["quality"])
        if validation["validator"]["exit_code"] != 0:
            append_event(workspace, job_id, "failed", "validation_failed", "案例草稿未通过 package 校验。")
            raise OutputValidationError("generated case draft failed package validation; see artifacts/validation.json.")

        append_event(workspace, job_id, "awaiting_review", "stage_completed", "案例草稿通过校验，等待人工审阅；尚未发布。")
        return package_dir
    except ProviderResponseFormatError as error:
        write_json(
            artifact_dir / "provider-response-diagnostic.json",
            {
                "provider": error.provider_name,
                "finish_reason": error.finish_reason,
                "content_length": len(error.content),
                "content": error.content,
                "recorded_at": utc_now(),
                "note": "Private provider content only; no request headers or credentials are recorded.",
            },
        )
        append_event(workspace, job_id, "failed", "provider_format_failed", str(error))
        raise
    except Exception as error:
        append_event(workspace, job_id, "failed", "stage_failed", str(error))
        raise


def revalidate_private_draft(*, jobs_root: Path, job_id: str) -> Path:
    """Re-run validation for an existing private draft without another LLM call."""
    workspace = jobs_root / job_id
    artifact_dir = workspace / "artifacts"
    package_root = artifact_dir / "package"
    packages = [path for path in package_root.iterdir() if path.is_dir()] if package_root.exists() else []
    if len(packages) != 1:
        raise OutputValidationError("expected exactly one private package under artifacts/package for revalidation.")
    package_dir = packages[0]
    case_json_path = package_dir / "case.json"
    case_json = read_json(case_json_path)
    normalize_source_quality(case_json)
    write_json(case_json_path, case_json)
    markdown_path = package_dir / "case.md"
    markdown_path.write_text(
        ensure_selected_images_embedded(markdown_path.read_text(encoding="utf-8"), case_json), encoding="utf-8"
    )

    append_event(workspace, job_id, "validating", "revalidation_started", "正在重新运行现有案例包校验。")
    validation = run_package_validation(job_id=job_id, package_slug=package_dir.name, package_dir=package_dir)
    write_json(artifact_dir / "validation.json", validation)
    if validation["validator"]["exit_code"] != 0:
        append_event(workspace, job_id, "failed", "validation_failed", "案例草稿未通过重新校验。")
        raise OutputValidationError("private case draft failed package validation; see artifacts/validation.json.")
    append_event(workspace, job_id, "awaiting_review", "revalidation_completed", "案例草稿通过重新校验，等待人工审阅。")
    return package_dir


def validate_confirmation(*, confirmation: dict[str, Any], job_id: str, disambiguation: dict[str, Any]) -> dict[str, Any]:
    if confirmation.get("job_id") != job_id:
        raise OutputValidationError("confirmation job_id does not match the job.")
    candidate_id = str(confirmation.get("candidate_id", "")).strip()
    if not candidate_id:
        raise OutputValidationError("confirmation candidate_id must not be empty.")
    confirmed_by = confirmation.get("confirmed_by")
    if not isinstance(confirmed_by, dict) or not str(confirmed_by.get("user_id", "")).strip():
        raise OutputValidationError("confirmation.confirmed_by.user_id is required.")
    candidates = disambiguation.get("candidates")
    if not isinstance(candidates, list):
        raise OutputValidationError("stored disambiguation candidates are invalid.")
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
            return candidate
    raise OutputValidationError("confirmation candidate_id was not emitted by this job's disambiguation stage.")


def collect_research_results(*, request: dict[str, Any], candidate: dict[str, Any], max_results: int = 16) -> list[dict[str, Any]]:
    """Collect a deliberately varied source set, rather than one generic SERP."""
    collected: list[dict[str, Any]] = []
    seen: set[str] = set()
    # gooood's ordinary search page is frequently a client-side shell. Its
    # documented WordPress endpoint is a bounded, auditable fallback.
    for item in search_gooood_api(str(candidate.get("project_name") or "")):
        url = normalize_url(str(item.get("url", "")))
        if not url or url in seen:
            continue
        seen.add(url)
        collected.append({
            "rank": len(collected) + 1, "title": str(item.get("title") or url), "url": url,
            "snippet": str(item.get("snippet", "")), "page_excerpt": str(item.get("page_excerpt", "")),
            "source_route": "gooood_api", "source_level_hint": "level_b", "retrieved_at": utc_now(),
        })
    for query in build_source_queries(request, candidate):
        for item in search_web(query, max_results=4):
            url = str(item.get("url", "")).strip()
            normalized = normalize_url(url)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            excerpt = fetch_page_excerpt(url, max_characters=12_000)
            collected.append({
                "rank": len(collected) + 1, "title": str(item.get("title") or url), "url": url,
                "snippet": str(item.get("snippet", "")), "page_excerpt": excerpt,
                "source_route": classify_source_route(url), "source_level_hint": classify_source_level(url),
                "retrieved_at": utc_now(),
            })
            if len(collected) >= max_results:
                return collected
    return collected


def search_gooood_api(project_name: str) -> list[dict[str, str]]:
    if not project_name:
        return []
    endpoint = f"https://dashboard.gooood.cn/api/wp/v2/posts?search={quote_plus(project_name)}&per_page=8"
    try:
        request = Request(endpoint, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception:
        return []
    results: list[dict[str, str]] = []
    for post in payload if isinstance(payload, list) else []:
        slug = str(post.get("slug") or "").strip()
        title = re.sub(r"<[^>]+>", "", unescape(str((post.get("title") or {}).get("rendered") or ""))).strip()
        content = re.sub(r"<[^>]+>", " ", unescape(str((post.get("content") or {}).get("rendered") or "")))
        if slug and title:
            results.append({"title": title, "url": f"https://www.gooood.cn/{slug}.htm", "snippet": "", "page_excerpt": re.sub(r"\s+", " ", content).strip()[:12000]})
    return results


def build_search_query(request: dict[str, Any], candidate: dict[str, Any]) -> str:
    project = request.get("project", {})
    terms = [
        candidate.get("project_name"),
        candidate.get("architect_or_studio"),
        candidate.get("location"),
        project.get("query") if isinstance(project, dict) else "",
        "architecture",
    ]
    unique = [str(value).strip() for value in terms if str(value or "").strip()]
    return " ".join(dict.fromkeys(unique))


def build_source_queries(request: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    """Level A/B first, then the mandated Chinese supplementary fallback."""
    project = str(candidate.get("project_name") or (request.get("project") or {}).get("query") or "").strip()
    architect = str(candidate.get("architect_or_studio") or (request.get("project") or {}).get("architect_or_studio") or "").strip()
    base = " ".join(value for value in (project, architect) if value)
    queries = [
        f"{base} architecture", f"{project} site:archdaily.com", f"{project} site:gooood.cn",
        f"{project} site:archiposition.com", f"{project} 建筑 设计",
        f"{project} site:mp.weixin.qq.com 建筑", f"{project} site:zhihu.com 建筑",
    ]
    return list(dict.fromkeys(query for query in queries if query.strip()))


def classify_source_route(url: str) -> str:
    host = urlparse(url).netloc.lower()
    for name in ("archdaily", "gooood", "archiposition", "weixin", "zhihu"):
        if name in host:
            return name
    return "general"


def classify_source_level(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if any(token in host for token in ("archdaily", "gooood", "archiposition", "dezeen", "designboom")):
        return "level_b"
    if any(token in host for token in ("weixin", "zhihu")):
        return "level_c"
    return "unclassified"


def search_web(query: str, *, max_results: int) -> list[dict[str, str]]:
    # Yahoo currently exposes useful server-rendered cards to this runtime.
    # Bing and DuckDuckGo are fallbacks; the latter can present a CAPTCHA to
    # automated clients, which the worker never attempts to solve or bypass.
    results = _search_yahoo(query)
    if not results:
        results = _search_bing(query)
    if not results:
        results = _search_duckduckgo(query)

    deduplicated: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in results:
        url = normalize_url(item["url"])
        if not url or url in seen or not url.startswith(("http://", "https://")):
            continue
        seen.add(url)
        deduplicated.append({"title": unescape(item["title"]), "url": url, "snippet": unescape(item["snippet"])})
        if len(deduplicated) >= max_results:
            break
    return deduplicated


def _search_yahoo(query: str) -> list[dict[str, str]]:
    request = Request(
        f"https://search.yahoo.com/search?p={quote_plus(query)}",
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception:
        return []
    parser = _YahooParser()
    parser.feed(html)
    return parser.results


def _search_bing(query: str) -> list[dict[str, str]]:
    request = Request(
        f"https://www.bing.com/search?q={quote_plus(query)}",
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception:
        return []
    parser = _BingParser()
    parser.feed(html)
    return parser.results


def _search_duckduckgo(query: str) -> list[dict[str, str]]:
    request = Request(
        f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception:
        return []
    parser = _DuckDuckGoParser()
    parser.feed(html)
    return parser.results


def fetch_page_excerpt(url: str, *, max_characters: int = 5000) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=20) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "application/xhtml+xml"}:
                return ""
            html = response.read(1_000_000).decode("utf-8", errors="replace")
    except Exception:
        return ""
    parser = _TextParser()
    parser.feed(html)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()[:max_characters]


def collect_pdf_sources(*, request: dict[str, Any], workspace: Path) -> list[dict[str, Any]]:
    """Extract page-addressable PDF evidence without sending arbitrary file paths to the model."""
    options = request.get("research_options") or {}
    mode = str(options.get("source_mode", "web"))
    if mode not in {"pdf", "mixed"}:
        return []
    inputs = request.get("input_files") or []
    if inputs:
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError as error:
            raise OutputValidationError("PDF source mode requires pypdf; install worker_runtime/requirements.txt before running a PDF job.") from error
    source_dir = workspace / "artifacts" / "pdf-inputs"
    collected: list[dict[str, Any]] = []
    for item in inputs:
        raw_path = item.get("path") if isinstance(item, dict) else item
        path = Path(str(raw_path or ""))
        if path.suffix.lower() != ".pdf" or not path.is_file():
            continue
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", path.name).strip("-") or f"source-{len(collected) + 1}.pdf"
        copied = source_dir / safe_name
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, copied)
        pages: list[dict[str, Any]] = []
        try:
            reader = PdfReader(str(copied))
            for number, page in enumerate(reader.pages, 1):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append({"page": number, "text": re.sub(r"\s+", " ", text)[:6000]})
            page_count = len(reader.pages)
            extraction_note = "Text extracted page by page; visual drawings require human review where labels are not extractable."
        except Exception as error:
            page_count, extraction_note = 0, f"PDF text extraction failed: {error}"
        collected.append({
            "kind": "pdf_source", "id": f"pdf_{len(collected) + 1:02d}", "title": path.stem,
            "source_kind": "user_pdf", "file_name": safe_name, "source_path": str(copied),
            "file_path": f"sources/{safe_name}", "page_count": page_count, "pages": pages,
            "source_level_hint": "user_provided", "extraction_note": extraction_note,
        })
    return collected


def materialize_pdf_sources(*, package_dir: Path, sources: list[dict[str, Any]]) -> None:
    for source in sources:
        source_path = Path(str(source.get("source_path", "")))
        file_path = str(source.get("file_path", ""))
        if source_path.is_file() and file_path.startswith("sources/"):
            target = package_dir / file_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)


def collect_image_candidates(*, research_results: list[dict[str, Any]], image_root: Path, enabled: bool) -> list[dict[str, Any]]:
    """Use the existing image pipeline to collect a small, auditable image set."""
    if not enabled or not IMAGE_PIPELINE_PATH.exists():
        return []
    spec = importlib.util.spec_from_file_location("architect_image_pipeline", IMAGE_PIPELINE_PATH)
    if spec is None or spec.loader is None:
        return []
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    manifests: list[dict[str, Any]] = []
    for result in research_results[:4]:
        url = str(result.get("url", ""))
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=20) as response:
                html = response.read(1_500_000).decode("utf-8", errors="replace")
        except Exception:
            continue
        urls = module.extract_image_urls(html, url)[:4]
        if urls:
            manifests.append({"slug": f"source-{len(manifests) + 1}", "page_url": url, "source_site": urlparse(url).netloc, "image_urls": urls})
    if not manifests:
        return []
    report = module.download_manifest(manifests, image_root)
    candidates: list[dict[str, Any]] = []
    for index, record in enumerate(report.get("records", []), 1):
        source_path = Path(str(record.get("file_name", "")))
        suffix = source_path.suffix.lower() or ".jpg"
        file_name = f"images/research-{index:02d}{suffix}"
        downloaded = record.get("download_status") == "downloaded" and source_path.exists()
        width, height = module.image_dimensions(source_path) if downloaded else (0, 0)
        candidates.append({
            "id": f"img_{index:02d}", "file_name": file_name,
            "source_url": str(record.get("source_url", "")),
            "source_site": str(record.get("source_site", "")),
            "source_path": str(source_path) if downloaded else "", "width": width, "height": height,
            "download_status": "downloaded" if downloaded else "failed",
            "failure_reason": str(record.get("failure_reason", "")),
            "suggested_image_type": suggest_image_type(str(record.get("source_url", ""))),
        })
        if len(candidates) >= 12:
            break
    return candidates


def suggest_image_type(url: str) -> str:
    value = url.lower()
    rules = (("plan", "03_plan"), ("floor", "03_plan"), ("section", "04_section"),
             ("elevation", "05_elevation"), ("detail", "06_detail"), ("material", "06_detail"),
             ("diagram", "07_concept"), ("concept", "07_concept"), ("interior", "08_interior"),
             ("aerial", "02_site"), ("site", "02_site"))
    return next((image_type for token, image_type in rules if token in value), "09_analysis")


def validate_image_candidates(*, case_json: dict[str, Any], candidates: list[dict[str, Any]]) -> None:
    images = case_json.get("image_metadata")
    if not isinstance(images, list):
        raise OutputValidationError("case_json.image_metadata must be an array.")
    if not images:
        return
    allowed = {str(item["file_name"]): item for item in candidates}
    for image in images:
        if not isinstance(image, dict):
            raise OutputValidationError("case_json.image_metadata items must be objects.")
        file_name = str(image.get("file_name", ""))
        if file_name not in allowed:
            raise OutputValidationError("image metadata must use only worker-collected image candidates.")
        candidate = allowed[file_name]
        if image.get("source_url") != candidate["source_url"]:
            raise OutputValidationError("image metadata source_url must match its collected candidate.")
        if image.get("download_status") != candidate["download_status"]:
            raise OutputValidationError("image metadata download_status must match the worker image result.")


def materialize_selected_images(*, package_dir: Path, candidates: list[dict[str, Any]], case_json: dict[str, Any]) -> None:
    selected = {str(image.get("file_name", "")) for image in case_json.get("image_metadata", []) if isinstance(image, dict)}
    for candidate in candidates:
        if candidate["file_name"] not in selected:
            continue
        if not candidate.get("source_path"):
            continue
        target = package_dir / candidate["file_name"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Path(candidate["source_path"]).read_bytes())


def ensure_selected_images_embedded(markdown: str, case_json: dict[str, Any]) -> str:
    """Repair a common structured-output omission before the package gate runs."""
    missing: list[dict[str, Any]] = []
    for image in case_json.get("image_metadata", []):
        if not isinstance(image, dict) or image.get("download_status") != "downloaded":
            continue
        file_name = str(image.get("file_name", "")).replace("\\", "/").strip()
        if not file_name:
            continue
        pattern = re.compile(r"!\[[^\]]*\]\(" + re.escape(file_name) + r"\)")
        if not pattern.search(markdown):
            missing.append(image)
    if not missing:
        return markdown.strip() + "\n"
    additions = ["## 图像证据补充", "以下图片由研究链路自动补入，以保持结构化图片记录与正文同步。"]
    for image in missing:
        caption = str(image.get("caption") or image.get("recommended_use") or "研究图片").strip()
        additions.append(f"![{caption}]({str(image['file_name']).replace('\\\\', '/')})")
    return markdown.strip() + "\n\n" + "\n\n".join(additions) + "\n"


def build_draft_instructions() -> str:
    base = (TEMPLATE_ROOT / "worker-instructions.md").read_text(encoding="utf-8")
    stage = (TEMPLATE_ROOT / "case-draft-instructions.md").read_text(encoding="utf-8")
    # The Phase-1 worker only named these references. Full research needs the
    # actual standards in the model context, otherwise it can only imitate a
    # shallow case summary from its retrieval excerpts.
    references = [
        "source-quality.md",
        "architecture-analysis-taxonomy.md",
        "case-package-template.md",
    ]
    reference_text = "\n\n".join(
        f"## Full-research reference: {name}\n{(SKILL_ROOT / 'references' / name).read_text(encoding='utf-8')}"
        for name in references
    )
    return f"{base}\n\n{stage}\n\n{reference_text}"


def build_provider_draft_schema(*, result_schema: dict[str, Any], case_schema: dict[str, Any]) -> dict[str, Any]:
    """Embed the canonical schema while preserving its root-relative $refs."""
    schema = deepcopy(result_schema)
    embedded_case_schema = deepcopy(case_schema)
    schema["$defs"] = embedded_case_schema.pop("$defs", {})
    schema["properties"]["case_json"] = embedded_case_schema
    return schema


def validate_draft_result(
    draft: dict[str, Any], *, result_schema: dict[str, Any], case_schema: dict[str, Any]
) -> None:
    if not isinstance(draft, dict):
        raise OutputValidationError("case-draft provider output must be a JSON object.")
    try:
        Draft202012Validator(result_schema).validate(draft)
    except ValidationError as error:
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise OutputValidationError(f"case-draft result failed JSON schema at {path}: {error.message}") from error
    try:
        Draft202012Validator(case_schema).validate(draft["case_json"])
    except ValidationError as error:
        path = ".".join(str(part) for part in error.absolute_path) or "case_json"
        raise OutputValidationError(f"case-draft case_json failed canonical schema at {path}: {error.message}") from error


def validate_retrieved_source_urls(
    case_json: dict[str, Any], research_results: list[dict[str, Any]], pdf_sources: list[dict[str, Any]]
) -> None:
    allowed_urls = {normalize_url(str(item.get("url", ""))) for item in research_results}
    allowed_pdf_paths = {str(item.get("file_path", "")) for item in pdf_sources}
    sources = case_json.get("sources")
    if not isinstance(sources, list):
        raise OutputValidationError("case-draft result sources must be an array.")
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise OutputValidationError(f"case-draft result sources[{index}] must be an object.")
        source_url = normalize_url(str(source.get("url", "")))
        source_path = str(source.get("file_path", ""))
        is_allowed_pdf = source.get("source_kind") in {"user_pdf", "local_pdf"} and source_path in allowed_pdf_paths
        if source_url not in allowed_urls and not is_allowed_pdf:
            raise OutputValidationError(
                f"case-draft result sources[{index}].url was not returned by the controlled retrieval stage."
            )


def normalize_source_quality(case_json: dict[str, Any]) -> None:
    """Downgrade overclaimed source sufficiency instead of inventing evidence."""
    source_quality = case_json.get("source_quality")
    if not isinstance(source_quality, dict):
        return
    confirming_ids = source_quality.get("identity_confirming_source_ids")
    if source_quality.get("source_sufficiency_status") != "sufficient" or not isinstance(confirming_ids, list):
        return
    unique_ids = {str(source_id).strip() for source_id in confirming_ids if str(source_id).strip()}
    if len(unique_ids) >= 2:
        return
    source_quality["source_sufficiency_status"] = "partial"
    review_notes = source_quality.setdefault("manual_review_needed", [])
    if isinstance(review_notes, list):
        note = "Worker downgraded source sufficiency to partial because fewer than two identity-confirming source IDs were recorded."
        if note not in review_notes:
            review_notes.append(note)
    if case_json.get("information_confidence") == "high":
        case_json["information_confidence"] = "medium"


def run_package_validation(*, job_id: str, package_slug: str, package_dir: Path) -> dict[str, Any]:
    # The validator runs with the repository root as cwd; use an absolute
    # package path so a relative job workspace cannot be resolved against the
    # wrong directory.
    command = [sys.executable, str(VALIDATOR_PATH), str(package_dir.resolve())]
    completed = subprocess.run(command, cwd=WORKSPACE_ROOT, text=True, capture_output=True, check=False)
    quality: dict[str, Any] | None = None
    if completed.returncode == 0 and QUALITY_REVIEWER_PATH.exists():
        quality_command = [sys.executable, str(QUALITY_REVIEWER_PATH), str(package_dir.resolve()), "--format", "json"]
        quality_run = subprocess.run(quality_command, cwd=WORKSPACE_ROOT, text=True, capture_output=True, check=False)
        try:
            parsed = json.loads(quality_run.stdout)
            quality = parsed[0] if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict) else None
        except json.JSONDecodeError:
            quality = None
        if quality is None:
            quality = {
                "score": None,
                "grade": "unavailable",
                "diagnostic": (quality_run.stderr or quality_run.stdout).strip()[:1000],
            }
    return {
        "job_id": job_id,
        "package_slug": package_slug,
        "validator": {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
        "passed_for_review": completed.returncode == 0,
        "quality": quality,
        "completed_at": utc_now(),
    }


def make_package_slug(candidate_id: str) -> str:
    slug = re.sub(r"-\d{4}$", "", candidate_id.strip().lower())
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    if not slug or slug in {".", ".."}:
        raise OutputValidationError("confirmed candidate_id cannot be normalized to a safe package slug.")
    return slug[:80]


def normalize_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, ""))


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

#!/usr/bin/env python3
"""Local image collection, hashing, deduplication, and selection utilities."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import sys
import time
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

DEFAULT_MAX_PER_CASE = 8
DEFAULT_PHASH_DISTANCE = 6
TYPE_QUOTAS = {"01_hero": 2, "02_site": 1, "03_plan": 2, "04_section": 2,
               "05_elevation": 1, "06_detail": 2, "07_concept": 1,
               "08_interior": 2, "09_analysis": 2}
SOURCE_PRIORITY = {"official": 5, "architect": 5, "gooood": 4, "archdaily": 4,
                   "archiposition": 4, "有方": 4, "小红书": 2, "xiaohongshu": 2}


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalize_url(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value.strip())
    if not parsed.scheme or not parsed.netloc:
        return value.strip()
    keep = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if not k.lower().startswith(("utm_", "xsec_", "spm", "ref"))]
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path,
                       parsed.params, urlencode(keep), ""))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def image_dimensions(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image  # type: ignore
        with Image.open(path) as image:
            return image.width, image.height
    except Exception:
        return 0, 0


def phash(path: Path) -> str:
    """Return a 64-bit pHash; empty when Pillow is unavailable or invalid."""
    try:
        from PIL import Image  # type: ignore
        with Image.open(path) as source:
            image = source.convert("L").resize((32, 32))
            pixels = [[image.getpixel((x, y)) for x in range(32)] for y in range(32)]
        values: list[float] = []
        for u in range(8):
            for v in range(8):
                total = sum(pixels[y][x] * math.cos((2 * x + 1) * u * math.pi / 64)
                            * math.cos((2 * y + 1) * v * math.pi / 64)
                            for x in range(32) for y in range(32))
                alpha = 1 / math.sqrt(32) if u == 0 else math.sqrt(2 / 32)
                beta = 1 / math.sqrt(32) if v == 0 else math.sqrt(2 / 32)
                values.append(total * alpha * beta)
        middle = sorted(values[1:])[len(values[1:]) // 2]
        return "".join("1" if value > middle else "0" for value in values)
    except Exception:
        return ""


def hamming_distance(left: str, right: str) -> int | None:
    if not left or not right or len(left) != len(right):
        return None
    return sum(a != b for a, b in zip(left, right))


def source_score(item: dict[str, Any]) -> int:
    source = clean(item.get("source_site")).lower()
    return max((score for name, score in SOURCE_PRIORITY.items() if name.lower() in source), default=1)


def type_score(item: dict[str, Any]) -> int:
    return {"03_plan": 7, "04_section": 7, "06_detail": 6, "02_site": 6,
            "07_concept": 5, "05_elevation": 5, "08_interior": 4,
            "01_hero": 4, "09_analysis": 3}.get(clean(item.get("image_type")), 1)


def candidate_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    pixels = int(item.get("width") or 0) * int(item.get("height") or 0)
    return (-source_score(item), -type_score(item), -pixels, clean(item.get("asset_id")))


def iter_case_images(case_root: Path) -> Iterable[dict[str, Any]]:
    for json_path in sorted(case_root.rglob("case.json")):
        if "revisions" in json_path.parts:
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        folder = json_path.parent
        for index, metadata in enumerate(data.get("image_metadata") or []):
            if not isinstance(metadata, dict):
                continue
            filename = clean(metadata.get("file_name"))
            local = folder / filename if filename else None
            if not local or not local.is_file():
                continue
            width, height = image_dimensions(local)
            item = dict(metadata)
            item.update({"case_slug": folder.name, "case_path": str(folder),
                         "local_path": str(local), "width": width, "height": height,
                         "asset_id": clean(metadata.get("asset_id")) or f"{folder.name}:{index}"})
            item["source_url"] = normalize_url(clean(item.get("source_url")))
            item["sha256"] = sha256_file(local)
            item["phash"] = phash(local)
            yield item


def select_display_images(items: list[dict[str, Any]], max_per_case: int = DEFAULT_MAX_PER_CASE,
                          phash_threshold: int = DEFAULT_PHASH_DISTANCE) -> dict[str, list[dict[str, Any]]]:
    """Select deterministic, globally unique display assets without deleting files."""
    selected: dict[str, list[dict[str, Any]]] = defaultdict(list)
    used_sha: set[str] = set()
    used_phash: list[dict[str, Any]] = []
    per_type: dict[tuple[str, str], int] = defaultdict(int)
    for item in sorted(items, key=candidate_sort_key):
        case = clean(item.get("case_slug"))
        if not case or len(selected[case]) >= max_per_case:
            continue
        sha = clean(item.get("sha256"))
        if sha and sha in used_sha:
            continue
        if any((distance := hamming_distance(clean(item.get("phash")), clean(other.get("phash")))) is not None
               and distance <= phash_threshold for other in used_phash):
            continue
        image_type = clean(item.get("image_type"))
        if per_type[(case, image_type)] >= TYPE_QUOTAS.get(image_type, 2):
            continue
        output = dict(item)
        output.update({"dedupe_status": "unique", "duplicate_of": "", "dedupe_method": "",
                       "similarity_score": 0, "canonical_asset_id": clean(item.get("asset_id")),
                       "selection_score": source_score(item) * 10 + type_score(item)})
        selected[case].append(output)
        if sha:
            used_sha.add(sha)
        if clean(item.get("phash")):
            used_phash.append(output)
        per_type[(case, image_type)] += 1
    return dict(selected)


class ImageTagParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        for key in ("data-src", "data-original", "data-lazy-src", "src", "srcset", "data-srcset"):
            for part in values.get(key, "").split(","):
                candidate = part.strip().split(" ", 1)[0]
                if candidate and not candidate.startswith("data:"):
                    self.urls.append(candidate)


def extract_image_urls(page_html: str, page_url: str) -> list[str]:
    parser = ImageTagParser()
    parser.feed(page_html)
    found: list[str] = []
    seen: set[str] = set()
    for raw in parser.urls:
        url = normalize_url(urljoin(page_url, html.unescape(raw)))
        path = urlparse(url).path.lower()
        if not url or url in seen or any(token in path for token in ("logo", "avatar", "icon", "emoji")):
            continue
        if not re.search(r"\.(?:jpe?g|png|webp|gif|avif)(?:$|\?)", path):
            continue
        seen.add(url)
        found.append(url)
    return found


def fetch_bytes(url: str, retries: int = 3, timeout: int = 20) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(url, headers={"User-Agent": "ARCHITECT-research/1.0"})
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as error:
            last_error = error
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"download failed after {retries} attempts: {last_error}")


def gooood_candidates(query: str, per_page: int = 20) -> list[dict[str, Any]]:
    api = "https://dashboard.gooood.cn/api/wp/v2/posts?" + urlencode({"search": query, "per_page": per_page})
    payload = json.loads(fetch_bytes(api).decode("utf-8"))
    results: list[dict[str, Any]] = []
    for post in payload if isinstance(payload, list) else []:
        title = clean((post.get("title") or {}).get("rendered"))
        slug = clean(post.get("slug"))
        page_url = f"https://www.gooood.cn/{slug}.htm" if slug else clean(post.get("link"))
        content = clean((post.get("content") or {}).get("rendered"))
        urls = extract_image_urls(content, page_url)
        results.append({"title": re.sub(r"<[^>]+>", "", html.unescape(title)), "slug": slug,
                        "page_url": page_url, "source_site": "gooood", "candidate_count": len(urls),
                        "image_urls": urls})
    return results


def download_manifest(manifest: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    """Download candidate URLs with retry and an auditable per-item report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for article_index, article in enumerate(manifest):
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", clean(article.get("slug")) or f"article-{article_index}").strip("-")
        for image_index, url in enumerate(article.get("image_urls") or [], 1):
            requested_name = clean(article.get("file_names", {}).get(str(image_index))) if isinstance(article.get("file_names"), dict) else ""
            suffix = Path(urlparse(url).path).suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}:
                suffix = ".img"
            target = output_dir / (requested_name or f"{slug}-{image_index:03d}{suffix}")
            record = {"source_url": normalize_url(clean(url)), "source_page_url": clean(article.get("page_url")),
                      "source_site": clean(article.get("source_site")) or "gooood", "file_name": str(target),
                      "download_status": "failed", "attempts": 0, "failure_reason": ""}
            try:
                payload = fetch_bytes(url)
                target.write_bytes(payload)
                record["download_status"] = "downloaded"
                record["attempts"] = 1
                record["sha256"] = hashlib.sha256(payload).hexdigest()
            except Exception as error:
                record["attempts"] = 3
                record["failure_reason"] = str(error)
            records.append(record)
    report = {"candidate_images": len(records),
              "downloaded": sum(item["download_status"] == "downloaded" for item in records),
              "failed": sum(item["download_status"] == "failed" for item in records),
              "records": records}
    (output_dir / "download-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def write_index(case_root: Path, output_dir: Path, max_per_case: int, phash_threshold: int) -> dict[str, Any]:
    candidates = list(iter_case_images(case_root))
    selected = select_display_images(candidates, max_per_case, phash_threshold)
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = [asset for case in sorted(selected) for asset in selected[case]]
    (output_dir / "assets.jsonl").write_text("\n".join(json.dumps(asset, ensure_ascii=False) for asset in assets) + ("\n" if assets else ""), encoding="utf-8")
    hashes = {clean(asset.get("sha256")): clean(asset.get("asset_id")) for asset in assets if clean(asset.get("sha256"))}
    (output_dir / "hashes.json").write_text(json.dumps(hashes, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {"candidate_images": len(candidates), "selected_images": len(assets),
              "deduplicated": len(candidates) - len(assets), "cases": len(selected),
              "max_per_case": max_per_case, "phash_threshold": phash_threshold}
    (output_dir / "pipeline-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="ARCHITECT image pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="hash local case images and write a global index")
    scan.add_argument("--case-root", type=Path, default=Path("case-packages"))
    scan.add_argument("--output", type=Path, default=Path("image-index"))
    scan.add_argument("--max-per-case", type=int, default=DEFAULT_MAX_PER_CASE)
    scan.add_argument("--phash-threshold", type=int, default=DEFAULT_PHASH_DISTANCE)
    gooood = sub.add_parser("gooood", help="extract all image candidates from Gooood API results")
    gooood.add_argument("query")
    gooood.add_argument("--output", type=Path)
    download = sub.add_parser("download-manifest", help="download a Gooood-style candidate manifest with retries")
    download.add_argument("manifest", type=Path)
    download.add_argument("--output", type=Path, default=Path("image-downloads"))
    args = parser.parse_args()
    if args.command == "scan":
        print(json.dumps(write_index(args.case_root, args.output, args.max_per_case, args.phash_threshold), ensure_ascii=False, indent=2))
        return 0
    if args.command == "download-manifest":
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        print(json.dumps(download_manifest(manifest if isinstance(manifest, list) else [], args.output), ensure_ascii=False, indent=2))
        return 0
    results = gooood_candidates(args.query)
    text = json.dumps(results, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

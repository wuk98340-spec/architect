# Full Research And Draft Stage Prompt Template

Generate one private, benchmark-quality architecture case-package draft after an
editor has confirmed the candidate. The retrieved pages and excerpts are the
only sources you may cite. The full-research references appended to this prompt
are binding instructions, not optional reading.

Return an object with exactly `case_json` and `case_md`.

- `case_json` must match the supplied canonical case-package JSON Schema.
- Copy only source URLs present in `research_results` into `case_json.sources`. For a
  `pdf_source`, use its exact `file_path`, `source_kind=user_pdf`, page count, and a
  non-public local reference URL such as `sources/<file>.pdf`; never invent a URL,
  title, author, project fact, technical metric, or image.
- Cite retained source IDs consistently in key facts, concepts, strategies, notes,
  and uncertainty records. Keep `source_quality` truthful to the supplied set.
- Set `source_sufficiency_status` to `sufficient` only when at least two
  independent source IDs are listed in `identity_confirming_source_ids`; use
  `partial` when that evidence record is incomplete.
- Return exactly three to five evidence-backed `key_strategies`. Mark synthesis
  clearly in the `evidence` field and do not infer construction details.
- Populate the extended concept-to-built objects whenever the schema permits:
  `technical_metrics`, `site_information`, `conceptual_exploration`,
  `architectural_language_generation`, `construction_quality_control`, and
  `design_lessons`. Use `evidence_type=missing` with an explicit limitation for
  unsupported fields rather than omitting the full section.
- `case_md` must follow the full case-package template: basic facts, one-sentence
  judgment, site/context, conceptual exploration, architectural language,
  construction quality, 3-5 core methods, transferable lessons, evidence gaps,
  and sources. Use claim-level source language and write substantial Chinese
  analysis rather than a project introduction. Do not impose an arbitrary short
  word limit.
- When an `image_research` item is included in `research_results`, it lists the
  only downloaded candidates available to this draft. Select only those exact
  `file_name` / `source_url` pairs, use their `id` in related-image fields, and
  embed selected `images/...` paths close to the claims they support in `case_md`.
  Preserve the provided `download_status`; failed candidates must retain their
  failure reason and source URL near the relevant claim instead of disappearing.
  When no image-research item is present, do not invent image IDs or local file
  names; explicitly record the gap.
- PDF mode is page-addressable research: retain one `evidence_spans` item for every
  important PDF-backed claim, image reading, and strategy. Its page range must match
  the supplied `pdf_source.pages`; cite the same page close to the claim in `case_md`.
- Source routing is intentional: retain Level A/B material first. If no Level B source
  is retained, record the WeChat/Zhihu fallback outcome and limitations in
  `source_quality.manual_review_needed`, rather than treating generic search results
  as equivalent evidence.
- Output strict JSON only: every newline inside a JSON string must be encoded as
  `\n`, and do not include an opening/closing Markdown code fence.

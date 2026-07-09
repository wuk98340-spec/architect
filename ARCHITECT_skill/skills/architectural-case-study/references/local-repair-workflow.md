# Local Repair Workflow

Use this workflow when an existing case package already has `case.md` and `case.json`, and the user wants to improve only a specific part.

## Core Rules

- Treat local repair as a scoped edit, not a regeneration task.
- Before editing, back up the package with `scripts/backup_case_package.py <case-folder> --label <short-label>`.
- Read the relevant Markdown section and the related JSON fields before writing.
- Keep Markdown and JSON synchronized. If a claim, source, image, caption, strategy, or related image changes in one file, update the other file.
- Preserve the existing project identity, source levels, source IDs, image IDs, and section numbering unless the requested repair requires a change.
- Do not add new schema fields to `case.json`.
- Re-run `scripts/validate_case_package.py <case-folder>` after every repair.

## Choosing the Repair Target

If the user's target is explicit, repair only that target:

- "定位", "Positioning", or "5.2": update `## 05` / `### 5.2 定位 Positioning` and `case.json.conceptual_exploration.positioning` when present. If the package only has top-level `design_concept`, update that synthesis only when the positioning change affects the concept summary.
- "诊断" or "5.1": update `### 5.1 诊断 Diagnosis` and `case.json.conceptual_exploration.diagnosis` when present.
- "策略" or "5.3": update `### 5.3 策略 Strategy`, and update `case.json.conceptual_exploration.strategy` when present.
- "核心方法", "方法", or "第 08 章": update `## 08 核心方法提炼` and `case.json.key_strategies[]`.
- "建筑语言", "功能", "布局", "形体", or "氛围": update the matching `## 06` subsection and the matching `case.json.architectural_language_generation` field when present. Also update top-level `spatial_ideas` if the repaired paragraph changes the summary notes.
- "建造", "材料", "构造", or "施工": update the matching `## 07` subsection and `case.json.construction_quality_control` or top-level `materials_structure` when present.
- "设计启发" or "第 10 章": update `## 10 对我的设计启发` and `case.json.design_lessons` when present.
- "信息缺口", "冲突", or "第 11 章": update `## 11 信息缺口与冲突`, `case.json.uncertain_or_conflicting_info`, and `incomplete_reason` when needed.
- "图片", "图纸", "换图", "caption", or a specific image file/id: use the Image Repair rules below.

If the user does not identify the target, list the likely repair targets from the existing headings and image index, then ask which one to repair.

## Evidence Rules

- Existing sources are enough for wording, structure, emphasis, concision, and professional framing repairs.
- Search the web only when the repair introduces a new factual claim, adds or replaces a source, replaces an image, resolves a conflict, or strengthens a weak evidence area requested by the user.
- Do not upgrade confidence, source sufficiency, or source levels unless new evidence justifies the change.
- Keep evidence labels clear in Markdown: `来源明确`, `基于资料的归纳判断`, and `未检索到可靠资料`.
- If the repair removes a claim, remove or adjust stale source references and image references tied only to that claim.

## Text Repair

For a chapter or paragraph repair:

1. Locate the Markdown heading range and the JSON fields that represent the same content.
2. Rewrite only that range in `case.md`.
3. Update matching JSON notes, evidence notes, summaries, or arrays.
4. Keep existing source IDs unless the factual basis changes.
5. Keep existing image IDs unless the revised claim no longer matches an image.
6. If a local repair makes another nearby sentence inconsistent, adjust the smallest necessary neighboring sentence.

The repaired text should be more useful for architecture study: specific design problem, specific architectural operation, spatial or tectonic consequence, and evidence boundary.

## Strategy Repair

For `key_strategies[]` and `## 08 核心方法提炼`:

- Keep 3-5 strategies unless the user explicitly asks to change the count and validation still passes.
- Each strategy must retain: design problem, specific approach, architectural effect, evidence, source IDs, related image IDs, and transferable lesson.
- If replacing one strategy, update the corresponding Markdown method and the matching object in `case.json.key_strategies[]`.
- If strategy order changes in Markdown, reorder `case.json.key_strategies[]` to match.
- Do not keep a related image ID if the repaired strategy no longer makes the claim that image supports.
- When adding a new strategy from existing evidence, cite existing `sources[].id`. When sources are inadequate, search and add a new source object.

## Image Repair

Use image repair when replacing a single image, improving image metadata, changing a caption, or moving an image to a better section.

1. Identify the image by Markdown path, image index row, or `case.json.image_metadata[].id`.
2. Run backup with the image included, for example:

   ```bash
   python ARCHITECT_skill/skills/architectural-case-study/scripts/backup_case_package.py case-packages/<slug> --label replace-plan-image --image images/03_plan_gallery.jpg
   ```

3. For replacement images, search preferred Level A/B sources first: official pages, architect/studio pages, ArchDaily, ArchDaily China, gooood, 有方, Architectural Record, Dezeen, Divisare, or other credible architecture media.
4. Download the replacement into `images/` with a stable name such as `03_plan_repair_20260701.jpg`. Do not overwrite the old image unless the user explicitly requests it.
5. Update every affected Markdown embed near the relevant analysis.
6. Update `## 09 图纸与图片索引`.
7. Update `case.json.image_metadata[]`: `file_name`, `image_type`, `source_url`, `source_site`, `caption`, `copyright_note`, `recommended_use`, `relevance_reason`, `related_sections`, `download_status`, and `failure_reason`.
8. Update every `related_image_ids` reference if the image ID changes. Prefer keeping the existing image ID when the replacement serves the same analytical role.
9. If the new image cannot be downloaded, keep the original URL near the relevant paragraph, set `download_status` to `failed` or `skipped`, and explain `failure_reason`.

Do not use Pinterest, unsourced galleries, AI aggregation sites, or pages without usable image links.

## Validation Checklist

Before finishing, verify:

- The backup directory exists under `revisions/`.
- Only the requested scope changed, except for required consistency updates.
- `case.md` and `case.json` describe the same repaired content.
- Source IDs referenced by repaired content exist in `case.json.sources[]`.
- Image IDs referenced by repaired content exist in `case.json.image_metadata[]`.
- Downloaded replacement images exist under `images/`.
- The image index row matches the Markdown embed and JSON metadata.
- `scripts/validate_case_package.py <case-folder>` passes, or any remaining issue is clearly explained as pre-existing or outside the requested repair scope.

# Data Contract

The website generator reads shared root `case-packages` data and does not modify source case packages.

## Case Package Shape

Each case package should contain:

```text
case-packages/<slug>/
  case.json
  case.md
  images/        # optional
```

The generator recursively finds `case.json` files and skips paths containing `revisions`.

## Core Fields

The homepage and listing views primarily read:

- `project_name`
- `architects`
- `location`
- `year`
- `program`
- `status`
- `case_type`
- `information_confidence`
- `one_sentence_summary`
- `key_strategies`
- `image_metadata`
- `sources`

Detail pages render additional structured fields when present, including `key_facts`, `design_concept`, `site_context`, `technical_metrics`, `design_lessons`, `sources`, and `uncertain_or_conflicting_info`.

## Images

Only local files referenced by `image_metadata.file_name` are rendered. Missing remote images, undownloaded images, and empty filenames are skipped instead of generating broken placeholders.

The maintained site applies a non-destructive global image policy at build time:
SHA-256 exact duplicates and pHash near-duplicates are excluded from the
display gallery, each case is capped at eight selected images with type quotas,
and slide media does not reuse an image already shown in the same case. Source
`case.json` files are not rewritten by the site generator.

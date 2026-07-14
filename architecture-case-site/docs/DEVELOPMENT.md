# Development

## Build

```powershell
python .\scripts\build_site.py --config .\config.local.json
```

## Preview

```powershell
python -m http.server 8765 --bind 127.0.0.1 -d public
```

## Expected Checks

- The homepage opens.
- The case list count matches root `..\case-packages`.
- Search, type filters, region filters, and sorting work.
- Detail pages render structured fields from `case.json`.
- No missing local images render as broken placeholders.
- Desktop and mobile layouts have no horizontal overflow.
- Browser console has no unexpected errors.

## Image pipeline

Hash local case images and build a global, non-destructive asset index:

```powershell
python .\ARCHITECT_skill\scripts\image_pipeline.py scan `
  --case-root .\case-packages `
  --output .\image-index
```

The scan writes `assets.jsonl`, `hashes.json`, and `pipeline-report.json`.
The maintained site applies the same SHA-256/pHash and per-case quota policy in
memory during its normal build.

To inspect all image candidates exposed by Gooood's WordPress API:

```powershell
python .\ARCHITECT_skill\scripts\image_pipeline.py gooood "项目名称" `
  --output .\image-index\gooood-candidates.json
```

Download a reviewed candidate manifest with retry and failure reporting:

```powershell
python .\ARCHITECT_skill\scripts\image_pipeline.py download-manifest `
  .\image-index\gooood-candidates.json `
  --output .\image-downloads
```

## Repository Boundary

The website subproject owns layout, interaction, the generator, and generated `public/` output. Research automation and quality reports live in `..\ARCHITECT_skill`; shared source case data lives in `..\case-packages`.

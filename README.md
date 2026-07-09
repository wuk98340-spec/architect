# ARCHITECT Workspace

This repository is the single Git workspace for architecture case-study research, the project-local Codex skill, and the static case-library website.

## Project Structure

- `ARCHITECT_skill/`: Research automation, Codex skill files, quality reports, legacy site output, and exported artifacts.
- `architecture-case-site/`: Static website generator and generated `public/` site output.
- `case-packages/`: Shared source case data used by both subprojects.

The old sibling website repository at `C:\Users\dell\Desktop\architecture-case-site` is no longer the maintained location after this reorganization. Keep future website work inside `ARCHITECT\architecture-case-site`.

## Current Case Packages

- `anhui-museum-new-building-hgad`
- `baiyun-international-convention-center-phase-ii`
- `guangzhou-jiefang-middle-road-old-city-renewal`
- `hangzhou-national-version-museum-wenrun-ge`
- `he-art-museum`
- `jining-library`
- `lego-house`
- `qianhai-museum`
- `qingdao-international-conference-center`
- `raleigh-guizhou-big-project-activity-camp`
- `seashore-library`
- `shanghai-expo-china-pavilion`
- `shenzhen-international-communication-center`
- `suzhou-museum-new`
- `taizhou-folk-culture-exhibition-center`
- `taizhou-scientific-outlook-exhibition-hall`
- `west-village-basis-yard`

## Common Commands

Validate a case package:

```powershell
python "C:\Users\dell\Desktop\ARCHITECT\ARCHITECT_skill\skills\architectural-case-study\scripts\validate_case_package.py" `
  "C:\Users\dell\Desktop\ARCHITECT\case-packages\<slug>"
```

Review case quality:

```powershell
python "C:\Users\dell\Desktop\ARCHITECT\ARCHITECT_skill\scripts\review_case_quality.py" `
  "C:\Users\dell\Desktop\ARCHITECT\case-packages\<slug>" `
  --output "C:\Users\dell\Desktop\ARCHITECT\ARCHITECT_skill\quality-reports\<slug>-quality-report.md"
```

Rebuild the maintained website:

```powershell
cd "C:\Users\dell\Desktop\ARCHITECT\architecture-case-site"
python ".\scripts\build_site.py" --config ".\config.local.json"
```

Preview the generated site:

```powershell
python -m http.server 8765 --bind 127.0.0.1 -d public
```

## Organization Notes

- The canonical source for a case is `case-packages/<slug>/`.
- Website output is generated under `architecture-case-site/public/`.
- Skill/research outputs live under `ARCHITECT_skill/`.
- Images may exist in both `case-packages/` and generated website output because the build copies them for browser use. Do not manually merge those copies unless the build process changes.
- Keep temporary PDF page renders, extracted text, and one-off helper scripts in `tmp/`.
- Keep reusable workflow guidance in `ARCHITECT_skill/docs/`, not in `tmp/`.
- Clean Python `__pycache__/` folders freely; they are regenerated automatically.

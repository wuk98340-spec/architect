# Architectural Case Study Automation

This repository is a local workspace for architecture case-study research automation. It contains a project-local Codex skill, generated case packages, quality reports, and source data for the case-library website.

## Website Repository

The case-library website has been split into its own sibling Git repository:

```text
C:\Users\dell\Desktop\architecture-case-site
```

Use that repository for website layout, interaction, static-site generation, and `public/` output. This `ARCHITECT` repository remains the source workspace for the skill and case data.

The website reads this repository's case data through configuration:

```json
{
  "casePackagesDir": "C:/Users/dell/Desktop/ARCHITECT/case-packages",
  "outputDir": "public"
}
```

Do not manually edit `ARCHITECT/site` for future website work. Treat the sibling website repository as the maintained website project.

## Project Structure

- `skills/architectural-case-study/`: Codex skill and references for creating cited architecture case-study packages.
- `case-packages/`: Source case packages. Each case folder should contain `case.md`, `case.json`, and optional local images, drawings, references, evidence, or revision backups.
- `scripts/`: Project utilities, including legacy static-site generation and quality review.
- `quality-reports/`: Markdown quality reports generated from case packages.
- `site/`: Legacy generated static case-library site. The maintained website now lives in `..\architecture-case-site`.
- `output/`: Exported final artifacts such as PDFs.
- `docs/`: Workflow notes and project documentation.
- `tmp/` and `tmp-validation-case/`: Temporary extraction, rendering, and validation scratch space. These can be cleaned when no active task depends on them.

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
python "C:\Users\dell\Desktop\ARCHITECT\skills\architectural-case-study\scripts\validate_case_package.py" `
  "C:\Users\dell\Desktop\ARCHITECT\case-packages\<slug>"
```

Review case quality:

```powershell
python "C:\Users\dell\Desktop\ARCHITECT\scripts\review_case_quality.py" `
  "C:\Users\dell\Desktop\ARCHITECT\case-packages\<slug>" `
  --output "C:\Users\dell\Desktop\ARCHITECT\quality-reports\<slug>-quality-report.md"
```

Rebuild the maintained website from the sibling repository:

```powershell
cd "C:\Users\dell\Desktop\architecture-case-site"
python ".\scripts\build_site.py" --config ".\config.local.json"
```

Preview the generated site:

```powershell
python -m http.server 8765 --bind 127.0.0.1 -d public
```

## Organization Notes

- The canonical source for a case is `case-packages/<slug>/`; website output is generated in the sibling website repository.
- Images may exist in both `case-packages/` and the website repository's `public/` output because the build copies them for browser use. Do not manually merge those copies unless the build process is changed.
- Keep temporary PDF page renders, extracted text, and one-off helper scripts in `tmp/`.
- Keep reusable workflow guidance in `docs/`, not in `tmp/`.
- Clean Python `__pycache__/` folders freely; they are regenerated automatically.

# ARCHITECT Skill Handoff

Read this before modifying the research automation subproject.

## Workspace Layout

The ARCHITECT repository is now a single Git workspace with three main areas:

- `ARCHITECT_skill/`: Codex skill, research scripts, quality reports, legacy generated site output, and exported artifacts.
- `case-packages/`: Shared source case data. This directory stays at the workspace root.
- `architecture-case-site/`: Maintained static website generator and generated `public/` output.

Do not duplicate `case-packages` inside `ARCHITECT_skill` or `architecture-case-site`.

## Important Paths

- Skill entrypoint: `ARCHITECT_skill/skills/architectural-case-study/SKILL.md`
- Source quality rules: `ARCHITECT_skill/skills/architectural-case-study/references/source-quality.md`
- Analysis taxonomy: `ARCHITECT_skill/skills/architectural-case-study/references/architecture-analysis-taxonomy.md`
- Markdown template: `ARCHITECT_skill/skills/architectural-case-study/references/case-package-template.md`
- JSON schema: `ARCHITECT_skill/skills/architectural-case-study/references/case-package-schema.json`
- Shared case data: `case-packages/<slug>/`
- Quality reports: `ARCHITECT_skill/quality-reports/`
- Legacy skill-generated site: `ARCHITECT_skill/site/`

## Case Package Rules

- Treat `case-packages/<slug>/case.md` as the readable Chinese study note.
- Treat `case-packages/<slug>/case.json` as the structured source of truth for validation, website generation, and future retrieval.
- Store downloaded research images in `case-packages/<slug>/images/`.
- Keep Markdown, JSON, local images, source IDs, captions, and image metadata synchronized.
- Do not invent technical metrics, structure, materials, dates, areas, construction details, or collaborators when sources are weak.

## Commands

Validate a case package from the workspace root:

```powershell
python "ARCHITECT_skill\skills\architectural-case-study\scripts\validate_case_package.py" "case-packages\<slug>"
```

Review case quality from the workspace root:

```powershell
python "ARCHITECT_skill\scripts\review_case_quality.py" "case-packages\<slug>" `
  --output "ARCHITECT_skill\quality-reports\<slug>-quality-report.md"
```

Build the legacy skill site:

```powershell
python "ARCHITECT_skill\scripts\build_site.py"
```

Build the maintained website:

```powershell
cd "architecture-case-site"
python ".\scripts\build_site.py" --config ".\config.local.json"
```

## Working Notes

- Prefer editing `case-packages`, skill references, or generator scripts, then rebuild outputs.
- `ARCHITECT_skill/site/` and `architecture-case-site/public/` are generated outputs; do not treat them as canonical source data.
- Some historical files may contain encoding damage. Do not copy corrupted text into new work; write new content as UTF-8.
- Before starting a case generation or repair task, inspect `git status --short --branch` and the target case folder.

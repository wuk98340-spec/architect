# ARCHITECT Skill

This subproject contains the architecture case-study automation skill, review scripts, quality reports, legacy generated site output, and exported artifacts.

## Shared Data

Case packages are intentionally stored one level above this subproject:

```text
C:\Users\dell\Desktop\ARCHITECT\case-packages
```

Do not duplicate `case-packages` into this folder. Scripts in this subproject read the shared root data directory.

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

Build the legacy local site output:

```powershell
python "C:\Users\dell\Desktop\ARCHITECT\ARCHITECT_skill\scripts\build_site.py"
```

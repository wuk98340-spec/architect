# Architectural Case Study Automation

This repository contains a project-local Codex skill for architecture case-study automation and generated case research packages.

## Contents

- `skills/architectural-case-study/`: Codex skill for creating concise, cited architecture case packages from public web sources.
- `case-packages/`: Generated case-study outputs. Each case folder contains:
  - `case.md`: human-readable Chinese case study notes.
  - `case.json`: structured data for future static-site or RAG ingestion.

## Current Case Packages

- `big-maze`
- `qian-xuesen-library-sjtu`
- `baiyun-international-hall`

## Validate A Case Package

Use the bundled validator:

```powershell
& "C:\Users\dell\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" `
  "C:\Users\dell\Desktop\ARCHITECT\skills\architectural-case-study\scripts\validate_case_package.py" `
  "C:\Users\dell\Desktop\ARCHITECT\case-packages\big-maze"
```

## Skill Usage

Ask Codex:

```text
Use C:\Users\dell\Desktop\ARCHITECT\skills\architectural-case-study to research <project name> and generate a case package.
```

The skill prefers official sources first, then architecture media, then general media, and marks uncertain or conflicting information instead of inventing missing facts.

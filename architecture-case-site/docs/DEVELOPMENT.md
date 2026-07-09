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

## Repository Boundary

The website subproject owns layout, interaction, the generator, and generated `public/` output. Research automation and quality reports live in `..\ARCHITECT_skill`; shared source case data lives in `..\case-packages`.

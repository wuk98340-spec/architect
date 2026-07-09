# Architecture Case Site

This subproject contains the static website generator and generated `public/` output for the architecture case library.

## Data Source

The site reads shared case data from:

```text
..\case-packages
```

`case-packages` belongs to the ARCHITECT workspace root. Do not copy case source data into this subproject.

## Structure

```text
architecture-case-site/
  config.example.json
  config.local.json        # local machine config, ignored by Git
  scripts/build_site.py    # static site generator
  public/                  # generated website output
  docs/
```

## Build

```powershell
python .\scripts\build_site.py --config .\config.local.json
```

If `config.local.json` is missing, the build falls back to `config.example.json`.

## Preview

```powershell
python -m http.server 8765 --bind 127.0.0.1 -d public
```

Then open:

```text
http://127.0.0.1:8765/
```

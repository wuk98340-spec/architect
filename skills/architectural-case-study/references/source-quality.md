# Source Quality Rules

Use these levels in `case.json.sources[].source_level`.

## official

Use for architect or studio project pages, client/owner pages, museum or institution pages, award-program pages, exhibition pages, city/government pages, and official press releases.

Trust official sources for names, participants, dates, location, program, status, and stated design intent. Still record conflicts if another credible source disagrees.

## architecture_media

Use for architecture and design media, including ArchDaily, Dezeen, Designboom, Divisare, Domus, Wallpaper, Architectural Record, World-Architects, The Architect's Newspaper, and comparable publications.

Use these sources for project descriptions, photographs, plans, interviews, interpretation, reception, and architectural context. Prefer media with named authors, dates, and clear image credits.

## general_media

Use for broad-interest media, newspapers, magazines, technology/culture publications, and local news.

Use these sources for public reception, event context, accessible descriptions, and quotes. Verify project facts against official or architecture-media sources when possible.

## reference_only

Use for Wikipedia, database mirrors, image aggregators, Pinterest, content farms, unsourced listicles, and AI-generated summaries.

Do not use these as the only source for a key fact. They can provide leads, alternate names, or search terms.

## Conflict Handling

Record a conflict when reliable sources disagree on project year, location, status, architect, collaborators, program, area, materials, or structural system.

Write conflicts in this form:

```json
{
  "topic": "Year",
  "description": "Official source lists 2014; media source describes the installation as opening in July 2014.",
  "source_ids": ["s1", "s2"]
}
```

If a field is not found after reasonable searching, leave the field empty or use "公开资料未确认" in Markdown, then add a note to `uncertain_or_conflicting_info`.

## Image Link Rules

Do not download images unless the user explicitly asks.

For each useful image, record:

- `url`: the page URL or direct image URL.
- `source_id`: the matching source id in `sources`.
- `intended_use`: cover candidate, exterior/context, plan/diagram, spatial sequence, material/detail, model/render, etc.
- `copyright_note`: image credit if visible, or a short note such as "Use as reference link only; rights not cleared."

Prefer page URLs with visible credit over bare CDN URLs.

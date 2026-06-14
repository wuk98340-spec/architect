# Source Quality Rules

Use these values in `case.json.sources[].source_level`:

- `level_a`
- `level_b`
- `level_c`
- `level_d`

Source quality determines confidence and wording. It does not by itself determine whether a case package can be generated.

## Level A: Official and Primary Sources

Use `level_a` for:

- Architect or studio project pages.
- Client, owner, museum, school, government, developer, or institution pages.
- Award program pages.
- Exhibition, competition, publication, or official press pages.

Use Level A first for project identity, names, participants, location, year, program, status, stated design intent, drawings, and image credits. Still record conflicts when credible sources disagree.

## Level B: High-Quality Architecture Media

Use `level_b` for architecture and design publications such as:

- gooood
- ArchDaily
- Archiposition / 有方
- Dezeen
- Designboom
- Divisare
- Architizer
- World-Architects
- Architectural Record
- Domus
- Wallpaper
- The Architect's Newspaper

Use Level B for project descriptions, photographs, plans, interviews, interpretation, reception, and architectural context. Prefer sources with named authors, dates, and visible image credits.

## Level C: Supplementary Chinese and Local Sources

Use `level_c` for:

- WeChat public-account articles.
- Reposted design media articles.
- Local architecture reports.
- School, institution, developer, or local news posts that are not official project pages.

For WeChat or Chinese search, include architecture-specific terms:

- `<project name> 建筑设计`
- `<project name> 设计解析`
- `<project name> 事务所`
- `<project name> 谷德`
- `<project name> 有方`
- `<project name> ArchDaily`
- `<project name> 平面图`
- `<project name> 剖面图`
- `<project name> 构造`

If several Level C sources corroborate one another, a case package can continue with medium or limited confidence. Explain the lack of Level A/B sources in `incomplete_reason` or `uncertain_or_conflicting_info`.

## Level D: Reference-Only Sources

Use `level_d` for:

- Baidu Baike.
- Wikipedia.
- Sohu, Zhihu, Douban, document-sharing sites.
- Pinterest.
- Unsourced image aggregators.
- AI summary pages.
- Database mirrors or content farms.

Do not use Level D as the only support for key facts when presenting them as certain. If only Level D is available, mark low confidence, state that the package is preliminary, and avoid strong professional claims.

## Confidence Guidance

- Level A/B exists: use it to confirm identity and core facts; confidence is usually high unless conflicts remain.
- Multiple corroborating Level C sources, no Level A/B: confidence is medium or "资料有限"; cite uncertainty for area, year, structure, material, and status.
- Mainly Level D: confidence is low; present only a preliminary research package.
- No sources: validation error.

## Conflict Handling

Record a conflict when sources disagree on project year, location, status, architect, collaborators, program, area, materials, or structural system.

Use this form:

```json
{
  "topic": "Year",
  "description": "Source s1 lists 2014; source s2 describes the project as opening in July 2015.",
  "source_ids": ["s1", "s2"]
}
```

If a field is not found after reasonable searching, leave it empty in JSON or write `公开资料未确认` in Markdown, then add a note to `uncertain_or_conflicting_info`.

## Image Link Rules

Do not download images unless the user explicitly asks. Still provide image links when they strongly support the written analysis.

For each useful image or drawing, record:

- `file_name`: local file name if downloaded, otherwise empty.
- `image_type`: one of the project image categories in `SKILL.md`.
- `source_url`: page URL or direct image URL.
- `source_site`: publisher or website.
- `caption`: concise description.
- `copyright_note`: credit if visible, or `Reference link only; rights not cleared.`
- `recommended_use`: cover, plan analysis, section analysis, facade analysis, material detail, circulation reference, etc.
- `related_sections`: section names or strategy IDs where the image is useful.
- `download_status`: `not_requested`, `downloaded`, `failed`, or `skipped`.
- `failure_reason`: required when `download_status` is `failed`.

Prefer Level A/B image pages with visible credits. Do not download from Pinterest, unsourced galleries, AI aggregation sites, or pages without direct usable image links. Downloading images is research organization, not commercial rights clearance.

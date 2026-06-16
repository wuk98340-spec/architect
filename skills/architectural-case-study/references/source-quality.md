# Source Quality Rules

Use these values in `case.json.sources[].source_level`:

- `level_a`
- `level_b`
- `level_c`
- `level_d`

Source quality determines confidence and wording. It does not by itself determine whether a case package can be generated. Do not treat missing Level A sources as an automatic failure; use Level A as the preferred identity calibration source.

## Source Sufficiency Gate

After searching Level A-D sources, assign `case.json.source_quality.source_sufficiency_status` before writing the final package.

Use `sufficient` when all are true:

- Project identity is clear.
- At least 2 mutually independent reliable sources confirm basic identity facts.
- Architectural analysis covers at least 3 items from `analysis_coverage`.

Use `partial` when project identity is clear, but any of these apply:

- Architectural analysis covers fewer than 3 items.
- Professional architecture media sources are few.
- Only 1 high-quality architecture media source was found.

Use `insufficient` when any of these apply:

- Project identity can only be weakly confirmed.
- Mainstream architecture media such as gooood, ArchDaily, 有方, Dezeen, Designboom, or Archiposition are missing.
- Architectural analysis mainly depends on WeChat, Zhihu, local reposts, or scattered media.

For `insufficient`, set `secondary_source_heavy` to `true`, explain the limitation in `incomplete_reason`, and state in `case.md` that project facts and design interpretations require manual review.

Use `ambiguous` when same-name projects, locations, architects, years, Chinese/English names, or project phases cannot be separated with confidence. Do not generate a full package; enter the Disambiguation Gate and output candidate projects for user confirmation.

### Identity Confirmation

Treat identity as clear when at least 2 mutually independent reliable sources corroborate the project name plus most of these facts:

- City / country.
- Architect / studio.
- Completion year or design year.
- Building type.

Mutually independent sources must not be simple reposts, translations, mirrors, or aggregations of the same original article.

### Analysis Coverage

Record covered topics in `case.json.source_quality.analysis_coverage` using only these values:

- `concept`
- `context`
- `program`
- `circulation`
- `facade_material`
- `structure_construction`
- `user_experience`
- `urban_relationship`

### Valid Search Results and Quotas

A valid search result must clearly discuss the target building case. Exclude same-name unrelated projects, pure image reposts, one-sentence mentions, unsourced marketing pages, and obvious AI rewrite pages. The result must include at least one of: project facts, design concept, spatial analysis, site relationship, material/structure information, or critical viewpoint. Count duplicate reposts as 1 valid result.

Search quotas are retained-result limits, not query limits:

| Sufficiency status | WeChat valid results | Zhihu valid results | Use |
| --- | ---: | ---: | --- |
| `sufficient` | 3 | 3 | Supplementary viewpoints only. |
| `partial` | 6 | 3 | Supplement design interpretation, Chinese commentary, spatial analysis, and user feedback. |
| `insufficient` | 9 | 3 | Secondary-source support; stop early if 3 consecutive new results add no new facts or analysis. |
| `ambiguous` | 0 | 0 | Do not generate; run the Disambiguation Gate. |

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

### gooood Search Fallback

Use this fallback before concluding that a Chinese architecture project is not on gooood.

1. Try ordinary search first:
   - `site:gooood.cn <project name>`
   - `site:gooood.cn <project name> 建筑`
   - `site:gooood.cn <architect/studio> <project name>`
   - `gooood <project name>`
   - `<project name> 谷德`
2. Try name variants:
   - Chinese simplified/traditional variants.
   - English project name, if known.
   - Architect/studio name plus city/province.
   - Common mistranscriptions or aliases from the Disambiguation Gate.
3. If ordinary search fails, query the gooood WordPress API directly:

```text
https://dashboard.gooood.cn/api/wp/v2/posts?search=<url-encoded keyword>&per_page=20
```

Search several keywords, starting broad and then narrowing:

- Full Chinese project name.
- Distinctive partial name.
- Architect/studio name.
- Province/city plus building type.
- English project name or organization name.

4. When an API result matches, use its `slug` to form the public article URL:

```text
https://www.gooood.cn/<slug>.htm
```

5. If the API JSON contains article content, extract:
   - Title, date, slug, and public URL.
   - Project facts near the article tail, such as project name, design office, year, area, location, client, photo credits.
   - Image URLs from `data-src` or `src` values under `https://oss.gooood.cn/uploads/...`.

6. Mark matching gooood articles as `level_b`. If the article states that content was provided by the design office, note this in `sources[].notes`; it can support higher confidence even though the publisher remains Level B.

Do not treat the visible gooood `/?s=<keyword>` page as definitive. It may return a front-end shell or homepage content that does not expose search results in server-rendered HTML.

## Level C: Supplementary Chinese and Local Sources

Use `level_c` for:

- WeChat public-account articles.
- Reposted design media articles.
- Local architecture reports.
- School, institution, developer, or local news posts that are not official project pages.
- Zhihu columns or answers only when they provide substantial architectural analysis with clear attribution; use them as supplementary analysis sources by default.

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
- Sohu, low-substance Zhihu posts, Douban, document-sharing sites.
- Pinterest.
- Unsourced image aggregators.
- AI summary pages.
- Database mirrors or content farms.

Do not use Level D as the only support for key facts when presenting them as certain. If only Level D is available, mark low confidence, state that the package is preliminary, and avoid strong professional claims.

Do not let Zhihu or WeChat carry the same weight as official sources or professional architecture media. They may help explain design readings, commentary, or user experience, but should not confirm identity unless the article has clear attribution and is corroborated by another independent reliable source.

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

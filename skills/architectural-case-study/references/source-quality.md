# Source Quality Rules

Use these values in `case.json.sources[].source_level`:

- `level_a`
- `level_b`
- `level_c`
- `level_d`

Source quality determines confidence and wording. It does not by itself determine whether a case package can be generated. Do not treat missing Level A sources as an automatic failure; use Level A as the preferred identity calibration source.

## Source Handling Order

Use this order before assigning the final sufficiency status:

1. Search Level A official and primary sources for identity, project facts, design intent, drawings, and image credits.
2. Search Level B professional architecture media, including gooood, ArchDaily / ArchDaily China, Archiposition / 有方, Dezeen, Designboom, and comparable publications.
3. For Chinese projects, always run the source-specific handling for gooood, ArchDaily / ArchDaily China, and Archiposition / 有方 before concluding that no mainstream architecture media source exists.
4. If at least one Level B source is retained, use Sogou WeChat and Sogou Zhihu as Level C supplementary searches for Chinese commentary, spatial readings, user experience, and additional leads.
5. If no Level B source is retained (`architecture_media_count = 0`), run the Mandatory WeChat / Zhihu Fallback before generating the package.
6. Use Level D sources only for orientation or weak background leads; do not use them as the sole basis for key facts.

Do not treat a search engine results page as a source. Only retain a result after opening or otherwise inspecting the target page enough to confirm that it discusses the intended building case.

### Mandatory WeChat / Zhihu Fallback When Level B Is Missing

When no Level B professional architecture media source is retained, WeChat and Zhihu are no longer optional. Before generating the package:

1. Run Sogou WeChat searches using the Sogou WeChat Search Handling rules below, plus ordinary web fallback queries if Sogou blocks access.
2. Run Sogou Zhihu searches using the Sogou Zhihu Search Handling rules below, plus ordinary web fallback queries if Sogou blocks access.
3. Try to retain up to the `insufficient` quota: 9 valid WeChat results and 3 valid Zhihu results.
4. Stop early only when any of these is true:
   - The retained-result quota is met.
   - 3 consecutive opened results add no new facts, analysis, image leads, design interpretation, or public/user-experience viewpoint.
   - Access is blocked by login, CAPTCHA, paywall, deleted article, or unavailable content.
5. If Sogou result snippets contain enough visible information to judge a WeChat or Zhihu result as valid, use that visible content directly in `case.md` and `case.json`. Include the account/author, title, visible snippet, and Sogou search URL or stable target URL when available.
6. If no valid WeChat or Zhihu result is retained, explicitly record why in `source_quality.manual_review_needed` and `uncertain_or_conflicting_info`.
7. Keep `source_sufficiency_status` as `insufficient` unless the mandatory fallback finds enough independent, substantive Level C sources to support identity and at least 3 analysis topics. Even then, confidence should usually be `medium` or `limited`, not `high`.

This fallback improves coverage; it does not upgrade WeChat or Zhihu to Level B. Do not use them alone for hard facts such as year, area, structure, material, architect/studio, or completion status unless corroborated by Level A or another reliable independent source.

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

### ArchDaily / ArchDaily China Search Handling

Use this handling before concluding that a project is absent from ArchDaily.

1. Search English and international pages:
   - `site:archdaily.com <project name>`
   - `site:archdaily.com <architect/studio> <project name>`
   - `ArchDaily <project name>`
   - `ArchDaily <architect/studio> <project name>`
2. Search Chinese pages and translated names when the project may have Chinese coverage:
   - `site:archdaily.cn <project name>`
   - `site:archdaily.cn <architect/studio> <project name>`
   - `ArchDaily 中国 <project name>`
   - `<project name> 建筑 ArchDaily`
3. Try name variants:
   - English project name.
   - Chinese project name.
   - Architect/studio name plus city/country.
   - Common shortened names from the Disambiguation Gate.
4. Retain ArchDaily project pages, interviews, feature articles, and pages with substantial project description as `level_b`.
5. Use ArchDaily primarily for:
   - English project name and title variants.
   - Architect/studio, location, year, program, area, and status when stated.
   - Design concept, plans, sections, photographs, and credits when visible.
6. Treat short news posts, roundups, and award-list mentions as supplementary only. They may stay `level_b` if published by ArchDaily, but note in `sources[].notes` that they do not independently support detailed analysis.

Do not assume the English and Chinese ArchDaily pages are independent if they are translations of the same article. Count translated or mirrored versions as one source for identity confirmation.

### Archiposition / 有方 Search Handling

Use this handling before concluding that a Chinese architecture project is absent from 有方.

1. Search targeted site and brand queries:
   - `site:archiposition.com <project name>`
   - `site:archiposition.com/items <project name>`
   - `<project name> 有方`
   - `<architect/studio> <project name> 有方`
   - `<project name> 建筑 有方`
2. Try Chinese and English variants:
   - Full Chinese project name.
   - Distinctive partial Chinese name.
   - English project name.
   - Architect/studio name plus city/province.
3. Retain 有方 project reports, interviews, research articles, and substantial design analysis as `level_b`.
4. Use 有方 for:
   - Chinese project naming, architect/studio, site context, and design description.
   - Professional interpretation, diagrams, photographs, and project background.
   - Leads to official or original sources mentioned in the article.
5. Treat events, lectures, awards roundups, directory listings, and brief mentions as supplementary only. Note the limited evidence value in `sources[].notes`.

Do not count reposts of the same 有方 article as independent sources. If the article states that content or images were provided by the architect/studio, note that provenance in `sources[].notes`.

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

### Sogou WeChat Search Handling

Use Sogou WeChat (`https://weixin.sogou.com/`) for supplementary Chinese public-account results. Use it after Level A/B searches or when searching for Chinese commentary and additional leads.

1. Search with architecture-specific terms:
   - `<project name> 建筑设计`
   - `<project name> 建筑`
   - `<project name> 设计解析`
   - `<project name> 事务所`
   - `<architect/studio> <project name>`
   - `<project name> 平面图`
   - `<project name> 剖面图`
   - `<project name> 构造`
2. Use brand-specific lead queries when Level B sources may exist:
   - `<project name> 谷德`
   - `<project name> 有方`
   - `<project name> ArchDaily`
3. When no Level B source is retained, add fallback-intent terms:
   - `<project name> 案例分析`
   - `<project name> 建筑赏析`
   - `<project name> 空间分析`
   - `<project name> 设计理念`
   - `<project name> 设计亮点`
   - `<project name> 建筑师`
   - `<project name> 竣工`
   - `<project name> 开放`
4. Retain only WeChat articles that clearly discuss the target building case and add at least one of:
   - Project facts.
   - Design concept or spatial analysis.
   - Site relationship.
   - Material, structure, or construction information.
   - Critical viewpoint, user experience, or professional commentary.
5. Exclude marketing posts, one-sentence mentions, unrelated same-name projects, pure image reposts, unsourced AI rewrites, and duplicate reposts of the same original article.
6. Mark retained WeChat public-account articles as `level_c` by default. If the article is merely a weak repost or lacks clear attribution, mark it as `level_d`.
7. If Sogou blocks access, shows CAPTCHA, or cannot expose article content, do not attempt to bypass it. Record the limitation in `manual_review_needed` or `uncertain_or_conflicting_info`, then try ordinary web queries such as:
   - `site:mp.weixin.qq.com <project name> 建筑设计`
   - `site:mp.weixin.qq.com <architect/studio> <project name>`
   - `site:mp.weixin.qq.com <project name> 案例分析`
   - `site:mp.weixin.qq.com <project name> 设计理念`
8. When a WeChat result is judged valid from the Sogou result page, add its visible content directly to the generated Markdown. Do not describe it only as a "lead"; summarize what it contributes, such as project-team confirmation, concept wording, status/opening timing, site relationship, public reception, or design interpretation.
9. When no Level B source is retained, do not leave `wechat_valid_result_count` at 0 unless all required fallback paths were tried or access was blocked. Explain the result in `manual_review_needed`.

WeChat can support interpretation and provide leads, but it should not carry core identity facts unless corroborated by at least one Level A/B source or another independent reliable source.

### Sogou Zhihu Search Handling

Use Sogou Zhihu (`https://zhihu.sogou.com/`) for supplementary Chinese discussion and learning-oriented perspectives. Use it after Level A/B searches or when looking for user experience, commentary, or design-study interpretations.

1. Search with architecture-specific terms:
   - `<project name> 建筑设计`
   - `<project name> 建筑`
   - `<project name> 空间`
   - `<project name> 设计解析`
   - `<architect/studio> 建筑`
   - `<architect/studio> <project name>`
2. When no Level B source is retained, add fallback-intent terms:
   - `<project name> 案例分析`
   - `<project name> 空间分析`
   - `<project name> 建筑赏析`
   - `<project name> 设计理念`
   - `<project name> 值得学习`
   - `<project name> 怎么样`
3. Retain Zhihu columns or answers as `level_c` only when they provide substantial architectural analysis, clear attribution, and concrete evidence or references.
4. Mark generic answers, unsourced opinions, weak reposts, schoolwork uploads, and low-substance discussion as `level_d`.
5. Use Zhihu mainly for:
   - User experience and public reception.
   - Design-study viewpoints.
   - Leads to official, media, or publication sources.
   - Critical questions that may guide `uncertain_or_conflicting_info`.
6. When a Zhihu result is judged valid from the Sogou result page, add its visible content directly to the generated Markdown. Do not describe it only as a "lead"; summarize what it contributes, such as learning viewpoint, public reception, design analogy, or a conflict to review.
7. Do not use Zhihu alone to confirm year, area, structure, material, architect/studio, or completion status.

Stop searching Zhihu after the retained-result quota is met, or earlier if 3 consecutive valid-looking results add no new facts, viewpoints, or leads.

### General Chinese Search Terms

For Chinese search beyond the specific Sogou engines, include architecture-specific terms:

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

# ARCHITECT 项目接手说明

这个文件是给以后进入本项目的 Codex / Agent 看的。先读这里，再动项目。不要每次都从零猜。

## 项目一句话

本项目是一个“建筑案例研究自动化 + 本地案例库”工作区：用项目内的 `architectural-case-study` 技能，从公开资料生成带引用、带结构化数据、带图片/图纸索引的建筑案例包，并把这些案例包构建成可本地浏览的静态案例库网站。

用户的核心需求不是百科摘要，而是建筑学意义上的案例研究：从概念、场地、空间语言、图纸、材料、构造到建成品质，提炼可迁移的设计方法。

## 当前项目状态

- 当前分支：`upgradeone`
- 最近主要升级：已加入本地静态案例库网站生成能力。
- 已有案例包目录：`case-packages/`
- 已有站点输出目录：`site/`
- 已有技能目录：`skills/architectural-case-study/`
- 已有 PDF 输出：`output/pdf/west-village-basis-yard-case-analysis.pdf`

当前案例包包括：

- `baiyun-international-convention-center-phase-ii`
- `lego-house`
- `qianhai-museum`
- `raleigh-guizhou-big-project-activity-camp`
- `seashore-library`
- `west-village-basis-yard`

历史 README 里列过旧案例名，但实际目录已经演进，接手时以 `case-packages/` 的真实内容为准。

## 目录职责

- `skills/architectural-case-study/SKILL.md`：项目内 Codex 技能主说明。生成新案例包前必须读。
- `skills/architectural-case-study/references/source-quality.md`：资料分级、搜索顺序、资料充分性判断、微信/知乎补充规则。
- `skills/architectural-case-study/references/architecture-analysis-taxonomy.md`：建筑分析框架，核心是“概念探索 / 建筑语言生成 / 建造品质控制”三层。
- `skills/architectural-case-study/references/case-package-template.md`：`case.md` 写作模板。
- `skills/architectural-case-study/references/case-package-schema.json`：`case.json` 结构约束。
- `skills/architectural-case-study/scripts/validate_case_package.py`：案例包校验脚本。
- `case-packages/<slug>/case.md`：中文可读案例研究笔记，图片应嵌入到相关分析段落附近。
- `case-packages/<slug>/case.json`：结构化案例数据，供校验、站点和未来 RAG 使用。
- `case-packages/<slug>/images/`：本地下载的分析相关图片/图纸。
- `scripts/build_site.py`：把案例包构建成 `site/` 静态网站。
- `site/`：构建后的本地静态案例库，不是手写主数据源。

## 已经做过的重要事情

1. 建立了项目级建筑案例研究技能 `architectural-case-study`。
2. 明确了资料优先级：官方/一手资料为 Level A，高质量建筑媒体为 Level B，微信/知乎/本地补充为 Level C，百科、搬运、弱来源为 Level D。
3. 增加了资料充分性判断：`sufficient`、`partial`、`insufficient`、`ambiguous`。
4. 增加了项目消歧门槛：名称、城市、设计方、年份、阶段不清时先列候选，不直接生成完整包。
5. 加入了 gooood、ArchDaily、ArchDaily China、Archiposition / 有方，以及微信/知乎补充搜索的工作流。
6. 扩展了 `case.json`：除了基础字段，还加入技术指标、场地信息、概念探索、建筑语言、建造品质、设计启示等结构。
7. 强化了图片工作流：图片不应只是装饰，必须有 `relevance_reason`，并嵌入 `case.md` 相关段落附近。
8. 增加了本地静态案例库生成脚本 `scripts/build_site.py`。
9. 增加了更严格的案例包校验，尤其检查图片下载状态、本地文件、Markdown 嵌入和来源引用。

## 生成新案例包的正确流程

默认输出位置：`case-packages/<slug>/`

1. 先读：
   - `skills/architectural-case-study/SKILL.md`
   - `references/source-quality.md`
   - `references/architecture-analysis-taxonomy.md`
   - `references/case-package-template.md`
   - `references/case-package-schema.json`
2. 先做消歧：
   - 如果项目名称可能对应多个项目、阶段、译名或设计方，先列候选表问用户确认。
   - 如果身份高置信，可以继续，但要在 `case.json.disambiguation_status` 里记录。
3. 搜索资料：
   - Level A：事务所、业主、官方、奖项、机构、竞赛或展览页。
   - Level B：ArchDaily、gooood、有方、Dezeen、Designboom、Divisare 等。
   - 中国项目必须特别查 gooood、ArchDaily / ArchDaily China、有方。
   - 如果没有 Level B，必须做微信/知乎补充搜索，并记录结果。
4. 建立 `case.md`：
   - 中文写作，保留必要英文项目名、事务所名、奖项和专业术语。
   - 不写泛泛介绍，要写“问题 - 做法 - 空间/建造结果 - 证据 - 可迁移方法”。
   - 资料不足处明确写缺口，不能猜面积、结构、构造、施工过程。
5. 建立 `case.json`：
   - 字段名严格按 schema 和 validator。
   - 来源要有 `id`，所有事实和策略要引用 `source_ids`。
   - 图片要有 `image_metadata`，包括 `relevance_reason`、`download_status`、版权/研究引用说明。
6. 下载并整理图片：
   - 默认创建 `images/`。
   - 优先下载场地、平面、剖面、立面、概念图、构造/材料、关键空间照片。
   - 不要下载 Pinterest、无来源图库、AI 聚合站、无法确认来源的图片。
   - 已下载图片必须在 `case.md` 用 Markdown 图片语法嵌入相关段落附近。
7. 运行校验。

## 校验与构建命令

优先使用项目可用的 Python。如果普通 `python` 不可用，可用 Codex runtime Python：

```powershell
& "C:\Users\dell\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" `
  "C:\Users\dell\Desktop\ARCHITECT\skills\architectural-case-study\scripts\validate_case_package.py" `
  "C:\Users\dell\Desktop\ARCHITECT\case-packages\<slug>"
```

构建静态案例库：

```powershell
python "C:\Users\dell\Desktop\ARCHITECT\scripts\build_site.py"
```

如果普通 `python` 不可用，改用上面的 runtime Python 执行 `scripts/build_site.py`。

构建后打开：

- `C:\Users\dell\Desktop\ARCHITECT\site\index.html`

## 写作质量标准

案例研究必须服务建筑设计学习，不要变成项目宣传稿。

每个案例至少要努力回答：

- 这个项目真正要解决什么问题？
- 概念如何转化为平面、剖面、动线、体量、界面或材料？
- 哪些判断来自明确来源，哪些是基于图纸/照片的归纳？
- 哪些技术指标、结构、构造或施工信息没有可靠资料？
- 这个案例能提炼出哪些可迁移的方法，而不是只能照抄形式？

策略写作优先 3-5 条，不要堆长目录。每条策略最好包含：

- 面对的问题
- 具体做法
- 建筑效果
- 证据来源
- 相关图片/图纸
- 可迁移方法

## 当前已知问题和接手注意

1. 部分中文内容存在编码乱码或问号替换问题。
   - `skills/architectural-case-study/references/case-package-template.md`、`source-quality.md`、`scripts/build_site.py` 以及部分历史案例包里可见乱码。
   - 后续不要继续复制乱码文本；新写内容应使用正常 UTF-8 中文。
   - 如果要修复，优先小范围修复当前要用的模板、站点文案和目标案例，不要一口气大改所有历史包。
2. `site/` 是构建产物。
   - 优先改 `case-packages/`、技能规则或构建脚本，再重新构建站点。
3. 有些旧案例 `download_mode` 仍是 `not_requested`，图片只保留链接；新案例应尽量完成本地图片下载和正文嵌入。
4. 版权状态必须谨慎：
   - 本地下载是研究整理，不代表商业发布授权。
   - `copyright_note` 应写清“研究引用，商业/公开发布需另行清权”。
5. 微信/知乎只能作为补充，不要用来单独确认年份、面积、结构、材料、设计方等硬事实。
6. 不要把缺少 Level A 误判为失败；真正要看身份是否确认、独立来源数量和分析覆盖度。

## 静态网站工作方式

`scripts/build_site.py` 会：

- 读取 `case-packages/*/case.md` 和 `case.json`
- 复制每个案例的 `images/`
- 生成 `site/index.html`
- 生成 `site/cases/<slug>/index.html`
- 写入 `site/assets/styles.css` 和 `site/assets/app.js`

所以如果要改网站样式或交互，改 `scripts/build_site.py` 里的 `STYLES` 和 `SCRIPT`，然后重新构建。不要只改 `site/assets/`，否则下次构建会被覆盖。

## 下次接手第一步

先做这三件事：

1. 看 `git status --short --branch`，确认有没有用户未提交改动。
2. 看 `case-packages/` 当前真实目录，而不是只信 README。
3. 如果任务涉及生成/修改案例，先读 `skills/architectural-case-study/SKILL.md` 和本文件，再开始。

## 与用户协作方式

用户希望项目能延续上下文。以后不要表现得像第一次见这个项目。

如果用户让你“继续做案例 / 生成案例 / 改案例库”，默认理解为：

- 使用项目内建筑案例研究技能。
- 保持中文专业写作。
- 保留证据纪律和来源分级。
- 校验 `case.json`。
- 必要时重新构建 `site/`。

如果发现前面内容混乱、乱码或旧包不符合新规则，先说明问题，再做最小必要修复。

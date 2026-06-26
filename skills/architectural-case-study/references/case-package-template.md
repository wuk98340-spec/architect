# Case Package Markdown Template

Use this template for `case.md`. Write concise, professional Chinese suitable for architecture study notes. Preserve English project names, studio names, awards, and precise architectural terms where useful.

The full frame guides searching and analysis; it is not a mandatory directory. Expand sections only when reliable sources, drawings, images, or clear project evidence support them. If a subsection has little evidence, merge it into a short limitation note instead of filling it with generic language.

Image rule: image handling is required by default. Embed downloaded images directly in the relevant body section with Markdown image syntax. Do not write only `img1/img2` IDs or leave useful images only in the index. If an image cannot be downloaded or should be skipped, keep its source link near the relevant paragraph with status and reason. Use `download_mode: not_requested` only when the user explicitly asks for link-only or no-image output; otherwise use `completed` or `partial`.

```markdown
# <项目名称> / <English Project Name>

> 不完整原因：<仅当资料不足、身份未完全确认、缺少 Level A/B、或只有 Level D 来源时填写；否则删除本行。资料不足且二手资料偏重时，必须写明“资料以二手资料为主，项目事实和设计解读需要人工复核”。>

## 01 基本信息与经济技术指标

| 项目 | 内容 |
| --- | --- |
| 项目名称 |  |
| 英文名称 |  |
| 建筑师 / 事务所 |  |
| 地点 |  |
| 国家 / 城市 |  |
| 建成年份 / 设计年份 |  |
| 建筑类型 |  |
| 用地面积 |  |
| 建筑面积 |  |
| 建筑高度 | 未检索到可靠资料 |
| 层数 | 未检索到可靠资料 |
| 容积率 | 未检索到可靠资料 |
| 建筑密度 | 未检索到可靠资料 |
| 结构体系 | 未检索到可靠资料 |
| 主要材料 |  |
| 业主 / 委托方 |  |
| 摄影 / 图纸来源 |  |
| 信息可信度 |  |
| 主要依据来源 |  |

> 指标说明：<如果建筑高度、容积率、建筑密度、结构体系等高精度资料缺失，在这里用一句话说明；不要猜测。>

## 02 资料质量与证据密度

- 资料状态：<sufficient / partial / insufficient / ambiguous>
- 是否有一级资料：<是 / 否>
- 一级资料是否用于身份确认：<是 / 否>
- 建筑专业媒体数量：
- 图片处理状态：<completed / partial；只有用户明确要求不要图片时才写 not_requested>
- 已覆盖分析项：<concept / context / program / circulation / facade_material / structure_construction / user_experience / urban_relationship>
- 资料最充分的方向：
- 资料明显不足的方向：
- 需要人工复核：

## 03 一句话判断

用 1-2 句话说明这个案例最值得学习的“从概念到建成”的方法。不要写成营销口号。

## 04 场地信息表

| 场地维度 | 与设计回应相关的信息 | 证据 |
| --- | --- | --- |
| 场地区位 |  |  |
| 自然环境 |  |  |
| 人文环境 |  |  |
| 地形条件 |  |  |
| 道路与交通 |  |  |
| 周边建筑特点 |  |  |
| 建筑服务人群 |  |  |
| 场地核心矛盾 |  |  |

> 场地资料不足说明：<仅当场地信息整体较少时保留。>

## 05 概念创意探索 Conceptual Exploration

### 5.1 诊断 Diagnosis

说明项目面对的核心问题、关键约束和可用资源。优先写来源明确的内容；必要时补充基于资料的归纳判断。

- 来源明确：
- 基于资料的归纳判断：

### 5.2 定位 Positioning

说明项目的地域文化、时代性、城市角色、使用者和体验目标。

- 来源明确：
- 基于资料的归纳判断：

### 5.3 策略 Strategy

说明主要设计策略是什么、回应了哪些问题、如何影响后续空间、形式和建造。

- 策略：
- 回应的问题：
- 对空间 / 形式 / 建造的影响：
- 证据来源：

### 5.4 意象与表达 Imagery, Naming & Expression

记录草图、概念图示、原型意象、命名、叙事或关键词。没有图示资料时，只概括公开资料中能确认的形象意图。

![概念图 / 草图说明](images/07_concept_example.jpg)
图文相关性：这张图用于说明<它支撑的概念生成、意象来源或形体判断>。

## 06 建筑语言生成 Architectural Language Generation

### 6.1 功能梳理 Function

分析使用人群、活动类型、程序逻辑、公共 / 私密关系、开放 / 封闭关系、功能复合或转译方式。

### 6.2 布局逻辑 Layout

分析总平面关系、平面组织、垂直组织、出入口与流线，以及建筑如何回应道路、景观、城市界面和外部限制。

![总平面 / 平面 / 流线图说明](images/03_plan_example.jpg)
图文相关性：这张图用于说明<它支撑的场地、功能、流线或平面判断>。

### 6.3 形式构成 Composition

分析体量生成、空间序列、界面处理、结构骨架与空间形式的关系、服务空间整合、表皮 / 开口 / 屋顶 / 地台的组织方式。

![剖面 / 立面 / 形体分析图说明](images/04_section_example.jpg)
图文相关性：这张图用于说明<它支撑的剖面、立面、体量或构造判断>。

### 6.4 场所与氛围 Place & Atmosphere

分析身体经验、视觉体验、光影、材料感知、内外关系、景观渗透、尺度关系，以及空间氛围如何服务项目定位。

## 07 建造品质控制 Construction Quality Control

> 本章只写有可靠来源支撑的内容。没有节点图、施工记录或材料说明时，不要根据常规做法推测。

### 7.1 建造语言 Construction Language

- 骨架：<结构体系、柱网、承重逻辑；无可靠资料则写“未检索到可靠资料”。>
- 围合：<外墙、幕墙、屋面、表皮；无可靠资料则写“未检索到可靠资料”。>
- 地台：<基座、平台、地面、景观基础；无可靠资料则写“未检索到可靠资料”。>

### 7.2 材料与工艺 Materials & Craft

说明主要材料、材料选择原因、加工方式、建造工艺，以及材料与地方性、经济性、耐久性、表现力之间的关系。

### 7.3 构造逻辑 Tectonic Logic

记录模数、展开面放样、剖切面层次、构造节点、表皮连接、屋面 / 墙身 / 地面等关键部位处理。没有可靠资料时，用一句话说明缺失。

### 7.4 物理性能与施工控制 Performance & Construction Control

说明防雨、防灰、遮阳、通风、保温隔热、室内外过渡、景观衔接、施工难点、现场加工、预制装配、样墙实验或质量控制措施。没有可靠资料时，用一句话说明缺失。

## 08 核心方法提炼

根据案例特色选择 3-5 个最有证据的策略或方法展开。每个策略应落在“问题 - 做法 - 效果 - 证据 - 可迁移方法”上。

### 方法 1：<方法名称>

- 面对的问题：
- 具体做法：
- 建筑效果：
- 证据来源：
- 相关图片 / 图纸：
  ![图片说明](images/03_plan_example.jpg)
  图文相关性：用于验证<该方法中的具体空间、构造、材料、流线或体验判断>。
  下载失败或跳过下载时写：[图片 / 图纸来源](URL)（下载状态：failed/skipped；原因：<原因>）
- 可迁移方法：

## 09 图纸与图片索引

| 图片类型 | 推荐用途 | 正文嵌入状态 / 本地图片 / 来源页面 | 来源 | 下载状态 | 图文相关性 | 版权 / 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| 01_hero | 封面 / 外观识别 | 已在正文嵌入：`images/01_hero_exterior.jpg` / [来源](URL) |  | downloaded | 用于说明整体外观识别与体量关系 |  |
| 02_site | 场地关系分析 | 已在正文嵌入：`images/02_site_context.jpg` / [来源](URL) |  | downloaded | 用于说明场地边界、道路或周边关系 |  |
| 03_plan | 平面 / 功能组织分析 | 已在正文嵌入：`images/03_plan_ground_floor.jpg` / [来源](URL) |  | downloaded | 用于说明功能、入口或流线组织 |  |
| 04_section | 剖面 / 空间关系分析 | 已在正文嵌入：`images/04_section_longitudinal.jpg` / [来源](URL) |  | downloaded | 用于说明剖面高差、空间序列或结构关系 |  |
| 05_elevation | 立面分析 | 已在正文嵌入：`images/05_elevation_main.jpg` / [来源](URL) |  | downloaded | 用于说明立面秩序、开口或表皮策略 |  |
| 06_detail | 构造 / 材料分析 | 已在正文嵌入：`images/06_detail_material.jpg` / [来源](URL) |  | downloaded | 用于说明材料、节点或构造逻辑 |  |
| 07_concept | 概念 / 生成逻辑 | 已在正文嵌入：`images/07_concept_diagram.jpg` / [来源](URL) |  | downloaded | 用于说明概念来源或生成过程 |  |
| 08_interior | 室内体验 | 已在正文嵌入：`images/08_interior_public_space.jpg` / [来源](URL) |  | downloaded | 用于说明室内体验、光线或公共性 |  |
| 09_analysis | 二次分析图素材 | 已在正文嵌入：`images/09_analysis_reference.jpg` / [来源](URL) |  | downloaded | 用于支撑二次分析判断 |  |

## 10 对我的设计启发

提炼该案例资料最充分、最有代表性的 3-6 条可迁移设计方法。不要面面俱到，也不要写泛泛概念启发。

- 可迁移方法 1：
- 可迁移方法 2：
- 可迁移方法 3：
- 不适合直接照搬的部分：
- 可转化成的分析图：

## 11 信息缺口与冲突

- 记录没有找到、仍存疑、或不同来源冲突的信息。
- 对经济技术指标、结构体系、构造节点、施工过程等高精度资料，缺失时明确说明，不要推测。
- 若缺少 Level A/B 来源，说明资料限制。
- 若只有 Level D 来源，明确标记为低可信、初步资料包。

## 12 来源列表

### Level A：官方与一手来源

- [来源标题](URL)

### Level B：高质量建筑媒体

- [来源标题](URL)

### Level C：中文补充源

- [来源标题](URL)

### Level D：参考源，只能辅助

- [来源标题](URL)
```

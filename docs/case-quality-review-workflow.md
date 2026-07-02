# 案例文字质量评分表与半自动审稿流程

这套机制以四个 PDF 标杆案例为校准样本：

- `guangzhou-jiefang-middle-road-old-city-renewal`
- `taizhou-folk-culture-exhibition-center`
- `shanghai-expo-china-pavilion`
- `suzhou-museum-new`

这些 PDF 标杆只用于校准“好文字长什么样”，日常评审不要求再提供 PDF。目标不是替代人工判断，而是把案例分析文字拆成可检查的论证链、证据语言、策略深度和建筑判断。自动评分负责发现硬伤，半自动审稿负责判断分析深度。

## 自动评分表

总分 100 分，建议阈值：

- 90-100：标杆级，可作为后续生成样本
- 80-89：可发布，但需要小修
- 70-79：需要修订后再入库
- 70 以下：建议重生成或大修
- `BLOCKED`：结构校验失败，先修 `case.json` / `case.md`

评分维度：

| 维度 | 分值 | 自动检查重点 |
| --- | ---: | --- |
| 包完整性 | 10 | `case.md`、`case.json`、既有 validator、标题、文本体量 |
| 文字论证链 | 20 | 是否形成“问题 - 方法 - 空间/建造成果 - 可迁移启发” |
| 策略与可迁移性 | 20 | 3-5 条策略，是否包含问题、做法、效果、证据、图片、可迁移方法 |
| 证据语言与资料纪律 | 15 | 来源等级、事实/策略 source refs、缺口记录；有 PDF 时才检查页证据 |
| 概念到建成覆盖 | 15 | 概念探索、建筑语言生成、建造品质控制、技术指标、场地信息 |
| 图像/图纸整合 | 5 | 图片元数据、本地文件、正文嵌入、图纸类型、图文相关性 |
| 文字深度与精确度 | 15 | 一句话判断、建筑词汇密度、资料不足说明、占位符、过泛表达 |

运行命令：

```powershell
python scripts/review_case_quality.py --benchmarks --output quality-reports/benchmark-quality-report.md
python scripts/review_case_quality.py case-packages/<slug>
python scripts/review_case_quality.py --output quality-reports/all-case-quality-report.md
```

如果普通 `python` 不可用，使用项目 README 中记录的 Codex runtime Python。

## 半自动审稿流程

第一轮先跑自动评分：

```powershell
python scripts/review_case_quality.py case-packages/<slug>
```

若出现 `BLOCKED` 或低于 70 分，先修结构、来源、策略字段和明显空泛段落，不进入人工深审。

第二轮人工审稿只看五件事：

| 审稿问题 | 合格判断 |
| --- | --- |
| 这个案例真正解决什么建筑问题？ | 不是项目介绍，而是能说清约束、矛盾或机会 |
| 概念如何变成空间/形式/构造？ | 能从诊断推到平面、剖面、体量、界面、材料或使用体验 |
| 文字是否有建筑判断？ | 能指出为什么这样做、解决了什么、带来什么空间或建造后果 |
| 判断是否贴着证据？ | 事实有来源，综合判断有图纸/照片/网页/PDF 页码，推测有标注 |
| 策略是否可迁移？ | 每条方法能被学生或设计者转化，而不是只描述项目特色 |
| 缺失资料是否诚实？ | 面积、结构、施工、节点不清楚时明确写缺口，不补写常识 |

第三轮按结论处理：

- 标杆级：保留为 future benchmark，并可作为 prompt 示例
- 小修：只修自动评分扣分项和人工审稿指出的薄弱段落
- 需修订：优先重写“一句话判断”“核心方法提炼”“概念到建成链条”和缺口说明
- 大修/重生成：重新进入 PDF Source Mode 或补充来源后再生成

## 标杆样本抽出的默认要求

新生成案例默认应满足：

- `key_strategies` 保持 3-5 条，每条都要有 source refs 和至少一个相关图像/图纸，除非资料确实缺失
- PDF 或 mixed source 案例必须有 `evidence_spans[]`，并在 `case.md` 中靠近论断标注 PDF 页码；非 PDF 案例不按这个要求扣重分
- `source_quality.analysis_coverage` 尽量覆盖 concept、context、program、circulation、facade_material、structure_construction、user_experience、urban_relationship
- 图片不只放进索引，必须嵌入正文相关段落，并写明 `relevance_reason`
- 缺少面积、结构、施工、节点等高精度信息时，宁可扣一点完整度，也不能编造
- 文字必须能读出“问题 - 方法 - 结果 - 可迁移启发”，不能只把项目资料改写成顺滑介绍

## 使用建议

这套评分应作为“入库前文字审稿”，不要作为唯一质量判断。自动分高只说明结构、证据语言和文字信号较好；最终是否标杆，还要人工判断它有没有形成清楚的“问题 - 方法 - 建筑结果 - 可迁移启发”链条。

# CloudBase Run 部署与 COS 存储

本项目包含两个 CloudBase Run 容器服务：

- `architect-api`：创建、查询、确认和保存案例研究任务。
- `architect-research-worker`：消费已确认的研究任务。

项目不再依赖 CFS、VPC 或 volume mount。容器内的 `/tmp/architect` 仅作为临时工作区；持久 job 和案例包由私有 COS 保存。

## 服务配置

| 服务 | 端口映射 | 网络 | 实例 |
| --- | --- | --- | --- |
| `architect-api` | `80 → 8080` | 开启公网访问 | `min=1`，`max=1` |
| `architect-research-worker` | `80 → 8080` | 仅内网访问 | `min=1`，`max=1` |

不要扩大 API 或 Worker 的实例数。当前 COS mirror 实现为单 API、单 Worker 设计；水平扩容前必须将任务 claim、幂等键和事件索引迁至支持租约/条件更新的数据库或队列。

## 运行时环境变量

两个服务均应配置：

```text
ARCHITECT_STORAGE_BACKEND=cos
ARCHITECT_COS_BUCKET=6172-architect-dev-d3g2rg2jfcda0906a-1457963611
ARCHITECT_COS_REGION=ap-shanghai
ARCHITECT_COS_PREFIX=architect
TENCENTCLOUD_SECRET_ID=<CAM 子用户 SecretId>
TENCENTCLOUD_SECRET_KEY=<CAM 子用户 SecretKey>
DEEPSEEK_API_KEY=<DeepSeek API key>
ARCHITECT_LLM_PROVIDER=deepseek
ARCHITECT_LLM_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
ARCHITECT_LLM_TIMEOUT_SECONDS=90
ARCHITECT_LLM_MAX_TOKENS=16000
```

`architect-api` 额外配置：

```text
ARCHITECT_SERVICE_ROLE=api
ARCHITECT_API_HOST=0.0.0.0
ARCHITECT_CORS_ORIGINS=https://architect-dev-d3g2rg2jfcda0906a-1457963611.tcloudbaseapp.com
```

`architect-research-worker` 额外配置：

```text
ARCHITECT_SERVICE_ROLE=worker
```

两个服务可显式使用以下临时缓存目录：

```text
ARCHITECT_DATA_ROOT=/tmp/architect
ARCHITECT_JOBS_ROOT=/tmp/architect/worker-jobs
ARCHITECT_CASE_PACKAGES_ROOT=/tmp/architect/case-packages
```

不要配置 `PORT`；CloudBase Run 会提供该变量。COS bucket 必须保持私有。使用无控制台登录权限的 CAM 子用户，仅授予该 bucket 的 `architect/*` 前缀读、写、列举和删除权限。

## COS 对象布局

| 数据 | COS key 前缀 |
| --- | --- |
| 请求、任务状态、草稿、PDF、图片、校验报告 | `architect/jobs/<job_id>/...` |
| 已发布案例包 | `architect/cases/<slug>/...` |

私有研究资产仅通过受控 API 路由读取；公开站点只应发布通过审核的案例与图片。

## Git 部署

选择包含 COS 提交的 Git 分支后再部署。自动部署应只绑定经过验证的专用分支；不要把它绑定到临时修复分支。首次发布后，在 CloudBase 控制台为两个服务设置上述环境变量和密钥。

## 本地开发

绕过 COS 时设置：

```powershell
$env:ARCHITECT_STORAGE_BACKEND = "local"
$env:ARCHITECT_DATA_ROOT = "$PWD\tmp\runtime-data"
$env:ARCHITECT_JOBS_ROOT = "$PWD\tmp\runtime-data\worker-jobs"
$env:ARCHITECT_CASE_PACKAGES_ROOT = "$PWD\tmp\runtime-data\case-packages"
cd ARCHITECT_skill
python -m backend_api.render_start
```

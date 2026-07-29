# CloudBase Run 部署

本项目包含两个 CloudBase Run 容器服务：

- `architect-api`：创建、查询、确认和保存案例研究任务。
- `architect-research-worker`：消费已确认的研究任务。

## 当前安全部署配置

两个服务使用完全相同的 COS 环境变量名称：

```text
ARCHITECT_STORAGE_BACKEND=cos
ARCHITECT_COS_BUCKET=<BucketName-APPID>
ARCHITECT_COS_REGION=<region，例如 ap-shanghai>
ARCHITECT_COS_PREFIX=architect
ARCHITECT_COS_SECRET_ID=<SecretId>
ARCHITECT_COS_SECRET_KEY=<SecretKey>
```

`cloudbaserc.json` 已为 API 与 Worker 使用这些相同名称。密钥只应在 CloudBase 控制台的受保护配置中提供，绝不写入 Git 或 `.env`；不要加首尾引号。

```text
DEEPSEEK_API_KEY=<DeepSeek API key>
ARCHITECT_LLM_PROVIDER=deepseek
ARCHITECT_LLM_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

服务启动时即使 COS 鉴权或网络失败，也会记录不泄密的诊断并回退到镜像内置案例库，不会因 COS 错误重启；后续需要 COS 的读取或保存会返回明确的 storage unavailable 错误。

## 部署

```powershell
$env:ENV_ID = "<CloudBase environment ID>"
$env:DEEPSEEK_API_KEY = "..."
cloudbase framework deploy
```

API 应配置 `ARCHITECT_SERVICE_ROLE=api` 和 `ARCHITECT_API_HOST=0.0.0.0`；Worker 应配置 `ARCHITECT_SERVICE_ROLE=worker`。不要设置 `PORT`，CloudBase Run 会自动注入。

## 将来启用持久存储

Bucket 必须填写完整的 `BucketName-APPID`。如需更高安全性，可在后续改用工作负载身份或短期凭据；当前实现会兼容旧的 `TENCENTCLOUD_SECRET_ID` / `TENCENTCLOUD_SECRET_KEY`，但新配置统一使用 `ARCHITECT_COS_SECRET_ID` / `ARCHITECT_COS_SECRET_KEY`。

## 本地开发

```powershell
$env:ARCHITECT_STORAGE_BACKEND = "local"
$env:ARCHITECT_DATA_ROOT = "$PWD\tmp\runtime-data"
$env:ARCHITECT_JOBS_ROOT = "$PWD\tmp\runtime-data\worker-jobs"
$env:ARCHITECT_CASE_PACKAGES_ROOT = "$PWD\tmp\runtime-data\case-packages"
cd ARCHITECT_skill
python -m backend_api.render_start
```

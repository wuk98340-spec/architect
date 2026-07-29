# CloudBase Run 部署

本项目包含两个 CloudBase Run 容器服务：

- `architect-api`：创建、查询、确认和保存案例研究任务。
- `architect-research-worker`：消费已确认的研究任务。

## 当前安全部署配置

默认部署使用容器本地运行时目录，不启用 COS，也不向服务注入腾讯云长期密钥：

```text
ARCHITECT_STORAGE_BACKEND=local
```

`cloudbaserc.json` 已为 API 与 Worker 设置该值。两项服务密钥只需在 CloudBase 控制台的受保护配置中提供，绝不写入 Git 或 `.env`：

```text
DEEPSEEK_API_KEY=<DeepSeek API key>
ARCHITECT_LLM_PROVIDER=deepseek
ARCHITECT_LLM_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

容器重启后，未发布的研究任务不会保留；已随镜像发布的案例库会自动恢复。服务启动时即使存在错误的旧 COS 配置，也会记录诊断并回退到镜像内置案例库，不会因 COS 错误重启。

## 部署

```powershell
$env:ENV_ID = "<CloudBase environment ID>"
$env:DEEPSEEK_API_KEY = "..."
cloudbase framework deploy
```

API 应配置 `ARCHITECT_SERVICE_ROLE=api` 和 `ARCHITECT_API_HOST=0.0.0.0`；Worker 应配置 `ARCHITECT_SERVICE_ROLE=worker`。不要设置 `PORT`，CloudBase Run 会自动注入。

## 将来启用持久存储

只有在改用工作负载身份或短期凭据，并完成读写、权限与重启恢复测试后，才可将 `ARCHITECT_STORAGE_BACKEND` 改为 `cos`。不要给运行中的容器配置长期 `SecretId` 或 `SecretKey`。

## 本地开发

```powershell
$env:ARCHITECT_STORAGE_BACKEND = "local"
$env:ARCHITECT_DATA_ROOT = "$PWD\tmp\runtime-data"
$env:ARCHITECT_JOBS_ROOT = "$PWD\tmp\runtime-data\worker-jobs"
$env:ARCHITECT_CASE_PACKAGES_ROOT = "$PWD\tmp\runtime-data\case-packages"
cd ARCHITECT_skill
python -m backend_api.render_start
```

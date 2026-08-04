# ARCHITECT → DigitalOcean 迁移交接

更新时间：2026-08-04

## 目标

将 ARCHITECT 建筑案例研究网站从腾讯云 CloudBase 迁移至 DigitalOcean：

- DigitalOcean App Platform 承载公网 API 与网站；
- DigitalOcean App Platform Worker 承载常驻研究任务；
- DigitalOcean Spaces 承载案例、任务和生成结果；
- DeepSeek 继续作为研究模型服务。

不要在迁移验收完成前删除 CloudBase 或 COS 数据。

## 当前线上状态

CloudBase 中现有两个服务：

- `architect-api`：网站和 API，公网可访问；
- `architect-research-worker`：已重新部署，作为后台任务 worker。

此前 CloudBase API 的 `/healthz` 返回 200，但 `/readyz` 返回 503；网站页面显示 `COS authentication failed: SignatureDoesNotMatch`。这表示 API 能启动，但 COS 访问失败。当前迁移不依赖修复该问题，但 CloudBase 应保留为回滚源，直至 DigitalOcean 完成真实任务验收。

## 已完成的本地改动

1. 新增 S3 兼容对象存储后端，保留原 COS 后端以便回滚：
   - `ARCHITECT_skill/backend_api/cos_storage.py`
   - 新增 `S3StorageConfig`、`S3StorageMirror`、`current_storage_mirror()`；
   - 使用 `boto3`，可对接 DigitalOcean Spaces；
   - `ARCHITECT_STORAGE_BACKEND=s3` 启用 S3 后端；`cos` 仍可用。

2. API、worker 与启动脚本已改为使用 provider-neutral 的存储工厂：
   - `ARCHITECT_skill/backend_api/app.py`
   - `ARCHITECT_skill/backend_api/render_start.py`
   - `ARCHITECT_skill/backend_api/research_worker.py`

3. 新增 DigitalOcean App Platform 双组件配置：
   - `.do/app.yaml`
   - Web Service：`architect-api`，端口 8080，健康检查 `/healthz`；
   - Worker：`architect-research-worker`；
   - 当前 GitHub 分支暂设为 `codex/local-repair-mode`，正式上线前应确认或改为发布分支。

4. 新增部署说明：
   - `DIGITALOCEAN_DEPLOYMENT.md`

5. 依赖与示例配置已更新：
   - `ARCHITECT_skill/worker_runtime/requirements.txt`：新增 `boto3>=1.35,<2`；
   - `ARCHITECT_skill/worker_runtime/.env.example`：新增 Spaces/S3 变量示例。

6. 测试已通过：

```powershell
cd C:\Users\dell\Desktop\ARCHITECT\ARCHITECT_skill
python -m unittest backend_api.tests.test_cos_storage backend_api.tests.test_render_start backend_api.tests.test_api
python -m compileall -q backend_api worker_runtime
```

结果：25 个测试通过；本机已安装 `boto3` 供验证。

## 工作区状态

当前分支：`codex/local-repair-mode`

当前尚未提交的改动包括：

- `ARCHITECT_skill/backend_api/app.py`
- `ARCHITECT_skill/backend_api/cos_storage.py`
- `ARCHITECT_skill/backend_api/render_start.py`
- `ARCHITECT_skill/backend_api/research_worker.py`
- `ARCHITECT_skill/backend_api/tests/test_cos_storage.py`
- `ARCHITECT_skill/backend_api/tests/test_render_start.py`
- `ARCHITECT_skill/worker_runtime/.env.example`
- `ARCHITECT_skill/worker_runtime/requirements.txt`
- `.do/app.yaml`
- `DIGITALOCEAN_DEPLOYMENT.md`
- 本交接文件。

在继续前应先检查 `git status --short --branch`。不要覆盖或丢弃现有改动。

## 下一步执行顺序

### 1. 创建 DigitalOcean 资源

在同一个 DigitalOcean Project 中：

1. 创建 App Platform App；
2. 创建私有 Spaces bucket，建议命名 `architect-production`；
3. 选择与应用相同区域。初始配置文件使用 `sgp` / `sgp1`（新加坡）；
4. 为应用创建专用 Spaces Access Key，授予该 bucket 的读写权限；
5. 连接 GitHub 仓库 `wuk98340-spec/architect`。

### 2. 配置 App Platform

导入或粘贴 `.do/app.yaml`。在 DigitalOcean 控制台中以 **Encrypted + RUN_TIME + App-level** 方式添加以下密钥和共享变量，不要将实际值写入 Git 或聊天：

```text
ARCHITECT_STORAGE_BACKEND=s3
ARCHITECT_S3_ENDPOINT=https://sgp1.digitaloceanspaces.com
ARCHITECT_S3_REGION=sgp1
ARCHITECT_S3_BUCKET=<Spaces bucket name>
ARCHITECT_S3_PREFIX=architect
ARCHITECT_S3_ACCESS_KEY_ID=<Spaces access key>
ARCHITECT_S3_SECRET_ACCESS_KEY=<Spaces secret key>

DEEPSEEK_API_KEY=<DeepSeek API key>
ARCHITECT_LLM_PROVIDER=deepseek
ARCHITECT_LLM_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
ARCHITECT_LLM_TIMEOUT_SECONDS=90
ARCHITECT_LLM_MAX_TOKENS=16000
```

服务专属变量已在 `.do/app.yaml` 中定义：

- API：`ARCHITECT_SERVICE_ROLE=api`
- Worker：`ARCHITECT_SERVICE_ROLE=worker`

注意：不要在 App Platform 中手动设置 `PORT`；平台负责注入，API 配置的 `http_port` 为 8080。

### 3. 迁移 COS 数据到 Spaces

迁移前，保留原有 key 名称。需要复制：

```text
architect/jobs/...
architect/cases/...
```

可用 rclone 或其他同时支持 COS 与 S3 的迁移工具。迁移后必须核对：

- 对象总数；
- 每个案例目录至少包含 `case.json`、`case.md` 与所需图片；
- 随机抽查任务及结果文件；
- Spaces bucket 保持私有。

### 4. 部署与验收

1. 部署 API 与 worker；
2. API `/healthz` 必须返回 200；
3. API `/readyz` 必须返回：

```json
{"status":"ready","storage":"ready"}
```

4. 从网站提交一条低成本测试研究任务；
5. 验证 worker 消费任务、调用 DeepSeek、将任务和结果写入 Spaces；
6. 验证 API 能读取并展示结果；
7. 最后绑定自定义域名并切 DNS。

建议在 DNS 切换后至少保留 CloudBase 48 小时，再考虑停用旧资源。

## 已知注意事项

- 当前代码运行时使用临时本地目录；所有持久化依赖 Spaces 的对象同步。不要依赖 App Platform 本地磁盘保存任务或案例。
- DigitalOcean App Platform 的 API 与 worker 应使用同一组 S3 配置，二者可独立扩缩容。
- 如果主要用户在中国大陆，先用 DigitalOcean 默认域名做真实可用性和延迟测试，再切换自定义域名。
- `SignatureDoesNotMatch` 属于 CloudBase/COS 的存储认证问题；迁到 Spaces 后不会沿用 COS 密钥。必须新建 Spaces Access Key。
- 当前 `.do/app.yaml` 是带占位符的部署声明，不能包含任何真实密钥。

## 新对话建议首句

```text
请继续执行 C:\Users\dell\Desktop\ARCHITECT\DIGITALOCEAN_MIGRATION_HANDOFF.md 中的 DigitalOcean 迁移。先检查当前 git 状态，再协助我创建/配置 App Platform 和 Spaces；不要修改或删除 CloudBase 资源，除非我明确确认。
```

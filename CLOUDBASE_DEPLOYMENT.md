# 腾讯云 CloudBase Run 部署

本项目现在可作为一个 CloudBase Run 容器服务部署：`Dockerfile` 启动同源的
静态网站和 API，`cloudbaserc.json` 声明 CloudBase Framework 的云托管服务及
CFS 挂载。

## 首次部署

1. 在腾讯云云开发控制台创建或选择一个环境，并记下环境 ID。
2. 在本机安装 CloudBase CLI，登录后执行：

   ```powershell
   $env:ENV_ID = "你的云开发环境 ID"
   cloudbase framework deploy
   ```

   也可以在云托管控制台选择“本地代码”，上传包含 `Dockerfile` 的仓库根目录。
   端口填 `8080`，公开访问选择 `WEB`。
3. 部署完成后，在云托管服务的环境变量中添加 `DEEPSEEK_API_KEY`。密钥绝不
   写入 `cloudbaserc.json` 或提交到 Git。
4. 在服务的“存储挂载”中确认 CFS `architect-case-library-cfs` 已挂载到
   `/var/data`。这个目录保存 jobs 和用户确认保存的案例库。

## 运行模型

- 对外入口：`/` 提供生成后的 `public/`，`/api/*` 提供后端，`/healthz` 为健康检查。
- 服务启动时会仅在 CFS 案例库为空时从镜像种子化案例，再由该持久库重建 `public/`。
- 已保存案例位于 `/var/data/case-packages`，任务位于 `/var/data/worker-jobs`。
- API 服务可继续使用 `low-cost` 模式、单实例并缩至 0；研究任务由下述独立队列
  Worker 执行。

## 异步研究 Worker

`POST /api/jobs/{job_id}/confirm` 只会把经过确认的任务写入
`/var/data/worker-jobs/<job_id>/research-task.json`，并返回 `202 Accepted`。
完整研究由独立的 CloudBase Run 服务执行，避免浏览器请求等待模型和网页检索。

创建一个名为 `architect-research-worker` 的第二个**容器型**服务，使用与
`architect-api` 相同的 Git 仓库、分支、Dockerfile、构建目录和所有 LLM 环境变量，
并额外配置：

```text
ARCHITECT_SERVICE_ROLE=worker
ARCHITECT_DATA_ROOT=/var/data
ARCHITECT_JOBS_ROOT=/var/data/worker-jobs
ARCHITECT_CASE_PACKAGES_ROOT=/var/data/case-packages
```

- 将与 API 完全相同的 CFS 文件系统挂载到两个服务的 `/var/data`。
- Worker 设置为仅内部访问，`MinNum=1`、`MaxNum=1`。单消费者避免重复研究；最小
  实例保证它能持续轮询 CFS 队列，而 API 仍可保持 `MinNum=0`。
- Worker 进程重启时会将 CFS 中遗留的 `research-task.running.json` 重新标记为
  `queued`；因此部署、扩缩容或实例故障不会丢失已确认的研究任务。

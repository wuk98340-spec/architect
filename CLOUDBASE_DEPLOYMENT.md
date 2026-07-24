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
- Blueprint 使用 `low-cost` 模式（可缩至 0）和单实例。当前 worker 仍是 API
  请求内同步运行；待改造成队列 worker 后再考虑扩容。

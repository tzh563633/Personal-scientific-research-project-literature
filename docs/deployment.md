# 部署手册

## Docker Desktop

1. 安装并启动 Docker Desktop，确保使用 Linux containers。
2. 在项目根目录复制 `.env.example` 为 `.env`。
3. 执行 `docker compose up --build`。
4. 浏览器打开 `http://localhost`，完成首次管理员初始化。
5. Mailpit 地址为 `http://localhost:8025`。

如果要启用 GROBID：

```powershell
docker compose --profile parsing up --build
```

本地模拟 RSS 验收可使用显式白名单覆盖：

```powershell
docker compose -f docker-compose.yml -f infra/compose.acceptance.yml up --build
```

该覆盖只允许 `host.docker.internal`，生产环境保持 `OUTBOUND_ALLOWED_HOSTS` 为空。

## 局域网访问

在 Windows PowerShell 中查看局域网地址：

```powershell
ipconfig
```

手机与电脑连接同一 Wi-Fi 后访问 `http://电脑局域网地址`。首次使用建议仅开放 Windows 防火墙中的本地网络访问。

## 宿主机 Agent

宿主机 Agent 只执行平台登记的业务动作，不执行任意 shell。启动前设置：

```powershell
$env:AGENT_TOKEN = "change-me-agent-token"
.\scripts\start-agent.ps1
```

远程指令会先进入 Agent 队列；如果没有启动 Agent，指令会保持 `pending`，不会在后端容器中绕过队列直接执行。

`SECRET_KEY`、`AGENT_TOKEN` 和 PostgreSQL 密码必须替换为随机值。首版局域网访问仍使用 HTTP，
因此只应在可信家庭/实验室网络中使用，不应直接暴露到公网。

## 备份与恢复

```powershell
.\scripts\backup.ps1
```

数据库由 `backup` 业务任务处理；`storage/` 文件由脚本压缩备份。恢复前停止服务，将备份文件恢复到 `storage/`，再启动 Compose。

应用备份目录包含 `database.dump` 和 `storage.zip`，可使用以下脚本恢复：

```powershell
.\scripts\restore.ps1 -BackupPath .\storage\backups\backup-YYYYMMDD-HHMMSS
```

脚本会恢复文件，并使用 backend 镜像中与备份生成端匹配的 `pg_restore` 恢复数据库。仅恢复文件时追加
`-SkipDatabase`。恢复前应停止 backend、worker 和 beat，恢复完成后再启动完整 Compose。

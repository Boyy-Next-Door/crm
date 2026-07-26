# Frappe CRM — 本地 Docker 部署指引

一次性打包，秒级启动，数据持久化。适用于在本机基于最新源码打镜像跑 CRM。

---

## 目录变化速览

相对官方的 `docker-compose.yml + init.sh` 每次启动都要重来的模式，新方案做了这些事：

- `docker/Dockerfile`：构建期完成 `bench init` / `get-app crm` / `bench build`，把所有 Python + Node 依赖固化进镜像。运行时不再联网拉包。
- `docker/entrypoint.sh`：首次启动时创建 `crm.localhost` 站点，之后启动只 `bench start`。默认站点语言写死为简体中文。
- `docker-compose.yml`：mariadb / redis / sites / logs 全部走 named volume，`docker compose down` 不再洗数据。
- `.dockerignore`：把 `node_modules` / `dist` / `dev-dist` / 构建产物排除掉，build context 小、可复现。
- 前端新增语言切换器（顶部导航栏）+ 默认语言改为 `zh`（`install.py` 里的 `after_install` hook 一次性写入 System Settings 和 Administrator 用户）。

---

## 前置条件

- Docker Desktop 或等价 Docker Engine，可用 `docker compose`（v2 语法）。
- 建议给 Docker 分配 ≥ 4GB 内存、≥ 20GB 磁盘（首次 build 会拉 Python + Node 依赖，成品镜像大概 2–3 GB）。
- 首次 build 需要联网。之后完全离线可跑。

---

## 第一次启动（在项目根目录 `frappe-crm/` 下执行）

```bash
# 1. 构建镜像（10–20 分钟，取决于网络和机器）
docker compose build

# 2. 启动
docker compose up -d

# 3. 观察首次建站日志（看到 "Site crm.localhost ready" 即成功）
docker compose logs -f frappe
```

打开浏览器访问：<http://crm.localhost:8000>

> Windows / macOS 若 `crm.localhost` 无法解析，改用 <http://localhost:8000>，或在 `hosts` 里加一行 `127.0.0.1 crm.localhost`。

登录：

- 用户：`Administrator`
- 密码：`admin`（可在 compose 里改 `ADMIN_PASSWORD`）

进来后语言默认是简体中文。如需切换语言，通过用户设置页（Frappe 桌面里 `User` 文档的 Language 字段）修改即可。

---

## 日常使用

```bash
docker compose up -d          # 启动（秒级）
docker compose stop           # 停止但保留容器和数据
docker compose start          # 再次启动
docker compose down           # 删容器，但 named volume 里的数据仍在
docker compose logs -f frappe # 看后端日志
```

进容器排查：

```bash
docker compose exec frappe bash
# 进去之后就在 /home/frappe/frappe-bench 目录，可以直接 bench --site crm.localhost console 等等
```

---

## 改了源码之后怎么办

**改后端 Python / hooks / DocType 定义** → 需要重打镜像：

```bash
docker compose build frappe
docker compose up -d
```

**改前端 Vue / 组件（比如以后要再扩展语言切换器）**  → 也是重打镜像，因为前端资源是在 build 阶段用 `bench build --production` 打进镜像的：

```bash
docker compose build frappe
docker compose up -d
```

**只是调翻译文件（`crm/locale/zh.po`）** → 同样重打镜像，po 文件会在下一次 `bench build` / 站点缓存刷新时生效。若想跳过重打：

```bash
docker compose exec frappe bench --site crm.localhost clear-cache
docker compose exec frappe bench --site crm.localhost migrate
```

**想边改边看（开发热更新）** → 不建议用这个镜像，那种场景下推荐官方原生的 `bench start` 本地开发流。此镜像的定位是「基于当前源码快照，稳定复现一份可跑的 CRM」。

---

## 数据持久化在哪

四个 named volume：

| Volume 名        | 内容                                     |
| ---------------- | ---------------------------------------- |
| `crm_mariadb-data` | MariaDB 数据库文件                       |
| `crm_redis-data`   | Redis 快照（缓存/队列）                  |
| `crm_sites-data`   | `frappe-bench/sites/`（含站点配置、公私钥、上传文件） |
| `crm_logs-data`    | `frappe-bench/logs/`                     |

查看：

```bash
docker volume ls | grep ^crm_
```

**彻底重置（危险，会清空所有数据）**：

```bash
docker compose down -v
docker compose up -d --build
```

---

## 常见问题排查

**Q: `docker compose build` 卡在 `bench get-app` 或 `yarn install`。**  
A: 通常是网络。可以在 Docker Desktop 里给容器配镜像源，或者在宿主机加代理然后 `docker compose build --build-arg HTTP_PROXY=... --build-arg HTTPS_PROXY=...`（Dockerfile 会自动尊重这些）。

**Q: 首次启动很久没进 CRM。**  
A: 看 `docker compose logs -f frappe`。首次要跑一次 `bench new-site` + `install-app crm`，大概 30–90 秒，看到 `Site crm.localhost ready` 才算好。

**Q: 想换端口。**  
A: 改 `docker-compose.yml` 里的 `ports: - "8000:8000"`，前面那个是宿主机端口，后面别动。

**Q: 想改数据库 root 密码。**  
A: 改两处：`mariadb.environment.MYSQL_ROOT_PASSWORD` 和 `frappe.environment.DB_ROOT_PASSWORD`。仅在第一次建库前改有效；改完记得 `docker compose down -v` 重建。

**Q: 我改了前端源码但页面没变化。**  
A: 你是不是只 `docker compose restart frappe` 了？前端是编译进镜像的，需要 `docker compose build frappe`。

**Q: 想把默认语言从中文改回英文。**  
A: 简单粗暴，改 `docker/entrypoint.sh` 里 `SITE_LANG` 默认或者在 compose 环境变量里设 `SITE_LANG=en`。或者进容器：

```bash
docker compose exec frappe bench --site crm.localhost set-config lang en
```

---

## 生产环境部署

生产环境相对开发有几个关键差异，通过环境变量控制：

| 变量 | 开发默认 | 生产建议 | 含义 |
|------|---------|---------|------|
| `MUTE_EMAILS` | `1` | `0` | `1` = 屏蔽所有出站邮件；`0` = 真正发送 |
| `DEVELOPER_MODE` | `1` | `0` | `1` = 代码自动重载 + 详细错误页；`0` = 生产模式 |
| `SERVER_SCRIPT_ENABLED` | `1` | `0` | 是否允许后台执行 Server Script（生产禁用避免风险） |
| `DB_ROOT_PASSWORD` | `123` | 强密码 | 数据库 root 密码 |
| `ADMIN_PASSWORD` | `admin` | 强密码 | 首次建站的 Administrator 密码 |
| `SITE_NAME` | `crm.localhost` | 真实域名 | 如 `crm.your-domain.com` |

### 部署方式：compose 覆盖文件

仓库里已经提供了 `docker-compose.prod.yml`，它覆盖 base compose 的关键字段。**生产环境用两个文件叠加启动**：

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

在启动前，先创建 `.env` 文件（放在项目根目录，跟 compose 文件同级）：

```dotenv
# .env — 生产环境敏感配置，别 commit
DB_ROOT_PASSWORD=SomeStrongDBPassword123!
ADMIN_PASSWORD=SomeStrongAdminPassword456!
SITE_NAME=crm.your-domain.com
```

`docker compose` 会自动读取 `.env`，把变量注入到 compose 文件中的 `${VAR}` 占位符。

`docker-compose.prod.yml` 里做了这些覆盖：

- `MUTE_EMAILS=0`、`DEVELOPER_MODE=0`、`SERVER_SCRIPT_ENABLED=0`
- 从 `.env` 读取 db/admin 密码 + 站点名
- **不暴露** MariaDB 的 `3306` 和 Redis 的 `6379` 到宿主机端口（DB/Redis 只在 compose 网络内可达，更安全）

### 全流程（干净的生产机器）

```bash
# 1. clone 源码
git clone <your-fork-url> frappe-crm
cd frappe-crm

# 2. 创建 .env
cat > .env <<EOF
DB_ROOT_PASSWORD=$(openssl rand -base64 24)
ADMIN_PASSWORD=$(openssl rand -base64 24)
SITE_NAME=crm.your-domain.com
EOF
chmod 600 .env
cat .env    # 记下 ADMIN_PASSWORD，第一次登录要用

# 3. build（首次 10-20 分钟）
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# 4. 启动
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 5. 观察启动日志，等到 "Site ... ready" 或 patch 都跑完
docker compose logs -f frappe
```

### 反向代理（推荐）

生产上不要直接把容器的 `8000` 端口暴露到公网，前面挂一个 Nginx 或 Caddy 处理 HTTPS + WebSocket：

```nginx
server {
    listen 443 ssl http2;
    server_name crm.your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/crm.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/crm.your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # socket.io（实时通知）
    location /socket.io/ {
        proxy_pass http://127.0.0.1:9000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### 邮件发送配置

`MUTE_EMAILS=0` 只是"允许出站邮件"，但还要有一个 Outgoing 邮箱账号才真的能发。生产上任选：

- 进 CRM → Settings → Email Accounts 手工加一个 SMTP（Gmail/Outlook/QQ/163/阿里云邮件推送等）
- 或者进 Frappe desk：`http://<域名>/app/email-account/new`
- 记得勾 `Enable Outgoing` + `Default Outgoing`，用 App Password 而不是登录密码

配好后自测：

```bash
docker compose exec frappe bench --site crm.localhost console
```
```python
frappe.sendmail(recipients=["you@example.com"], subject="Test", message="hi", now=True)
```

收到就通了。

### 生产环境改配置怎么办

**改 `.env` 里的变量**：

```bash
# 编辑 .env 后
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

`entrypoint.sh` 每次启动都会重新 apply `MUTE_EMAILS` / `DEVELOPER_MODE` / `SERVER_SCRIPT_ENABLED` 到 `site_config.json`，所以改完环境变量重启就生效。**首次建站时用的 `DB_ROOT_PASSWORD` / `ADMIN_PASSWORD` 不会自动改**——那两个只在第一次建站时用，后续修改需要用 `bench --site crm.localhost set-user-password` 或数据库工具。

### 备份策略（重要）

四个 named volume 里，**`sites-data` 和 `mariadb-data` 是必备**：

```bash
# 备份
docker run --rm -v crm_mariadb-data:/data -v $(pwd):/backup alpine \
    tar czf /backup/mariadb-$(date +%Y%m%d).tgz -C /data .
docker run --rm -v crm_sites-data:/data -v $(pwd):/backup alpine \
    tar czf /backup/sites-$(date +%Y%m%d).tgz -C /data .

# 或者用 Frappe 自带的 bench 命令
docker compose exec frappe bench --site crm.localhost backup --with-files
# 备份文件在 sites/crm.localhost/private/backups/，通过 volume 挂载能拿到
```

生产上建议：

- 每天自动 `bench backup` + rsync 到远程存储
- MariaDB volume 每周做一次全量 dump

---

## 附：镜像里改动了哪些源码文件（本次迭代）

- `crm/crm/install.py`（`after_install` 里加 `set_default_system_language`，默认语言写入 System Settings 和 Administrator 用户）
- `docker/Dockerfile`（新增）
- `docker/entrypoint.sh`（新增）
- `docker-compose.yml`（重写，加健康检查、named volume 持久化）
- `.dockerignore`（新增）

`init.sh` 保留在仓库里作为历史参考，不再被 compose 引用。

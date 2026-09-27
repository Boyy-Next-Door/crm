# 一台服务器跑两套独立 CRM（IP + 端口访问）

两个团队各用一套完全独立的环境：独立数据库、独立 Redis、独立站点数据、独立
管理员密码。互相看不到对方的数据，一套挂了不影响另一套。

```
http://<公网IP>:8081/crm   →  团队 A      http://<公网IP>/a  会 302 过去
http://<公网IP>:8082/crm   →  团队 B      http://<公网IP>/b  会 302 过去
```

> **为什么不是 `http://<IP>/a/crm` 这种纯路径？**
> Frappe 不支持子路径部署 —— 前端 router base 写死 `/crm`，`/api`、`/app`、
> `/files`、`/assets`、`/socket.io` 全是根路径，session cookie 也固定
> `Path=/`。要改成路径区分，得同时改前端 base、frappe-ui 的
> `requestBaseUrl`、socket.io 前缀、后端路由规则和 cookie path，而且每次合并
> 上游都要重打一遍补丁。端口方案零改动，所以选它。

---

## 架构

```
                 公网
                  │
        ┌─────────┴─────────┐
        │  宿主机 nginx      │   :80 (/a /b 跳转)  :8081  :8082
        └────┬─────────┬────┘
             │         │
   127.0.0.1:8001    127.0.0.1:8002      ← 容器端口只绑 localhost
   127.0.0.1:9001    127.0.0.1:9002         (socket.io)
             │         │
      ┌──────┴───┐ ┌───┴──────┐
      │ crm-a 栈  │ │ crm-b 栈  │           ← 两个 compose project
      │ frappe    │ │ frappe    │
      │ mariadb   │ │ mariadb   │
      │ redis     │ │ redis     │
      └───────────┘ └───────────┘
```

两套栈共用**同一个镜像** `frappe-crm:local`（只 build 一次），所以磁盘增量只有
第二份数据库，几十 MB 起步。

| | 团队 A | 团队 B |
|---|---|---|
| compose 项目名 | `crm-a` | `crm-b` |
| env 文件 | `.env.a` | `.env.b` |
| 站点名 | `crm-a.youruicheng.cn` | `crm-b.youruicheng.cn` |
| 宿主机 web 端口 | 8001 | 8002 |
| 宿主机 socketio 端口 | 9001 | 9002 |
| 公网端口 | 8081 | 8082 |
| 数据卷 | `crm-a_*` | `crm-b_*` |

站点名用 `*.youruicheng.cn` 是为了以后留退路：万一哪天域名备案下来了，把 DNS
指过来就能直接按域名访问，不用改站点。

---

## 部署步骤

以下都在服务器 `/youruicheng/crm` 下执行，需要 sudo。

### 1. 拉最新代码

```bash
cd /youruicheng/crm
sudo git fetch origin
sudo git checkout dev
sudo git pull
```

### 2. 写两个 env 文件

```bash
sudo tee /youruicheng/crm/.env.a >/dev/null <<EOF
SITE_NAME=crm-a.youruicheng.cn
DB_ROOT_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')
ADMIN_PASSWORD=$(openssl rand -base64 18 | tr -d '/+=')
WEB_PORT=8001
SOCKETIO_PORT=9001
EOF

sudo tee /youruicheng/crm/.env.b >/dev/null <<EOF
SITE_NAME=crm-b.youruicheng.cn
DB_ROOT_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')
ADMIN_PASSWORD=$(openssl rand -base64 18 | tr -d '/+=')
WEB_PORT=8002
SOCKETIO_PORT=9002
EOF

sudo chmod 600 /youruicheng/crm/.env.a /youruicheng/crm/.env.b
sudo cat /youruicheng/crm/.env.a /youruicheng/crm/.env.b   # 记下两个 ADMIN_PASSWORD
```

`ADMIN_PASSWORD` 只在**首次建站**时生效，记下来，第一次登录要用。

### 3. Build 镜像（只需一次）

```bash
cd /youruicheng/crm
sudo docker compose -p crm-a --env-file .env.a \
  -f docker-compose.yml -f docker-compose.prod.yml build
```

10–20 分钟。build 期间现有环境照常跑，不影响。

### 4. 起两套栈

```bash
cd /youruicheng/crm

sudo docker compose -p crm-a --env-file .env.a \
  -f docker-compose.yml -f docker-compose.prod.yml up -d

sudo docker compose -p crm-b --env-file .env.b \
  -f docker-compose.yml -f docker-compose.prod.yml up -d
```

第二条不会重新 build —— 镜像已经在了，直接复用。

看首次建站日志，等到 `Site ... ready`：

```bash
sudo docker compose -p crm-a --env-file .env.a -f docker-compose.yml -f docker-compose.prod.yml logs -f frappe
```

### 5. 配 nginx

```bash
sudo cp /youruicheng/crm/nginx-crm-multi.conf /etc/nginx/sites-available/crm-multi
sudo ln -sf /etc/nginx/sites-available/crm-multi /etc/nginx/sites-enabled/crm-multi

# 删掉会冲突的旧配置：default 也声明了 listen 80 default_server
sudo rm -f /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/crm

sudo nginx -t && sudo systemctl reload nginx
```

### 6. 开安全组

见下一节。

### 7. 验证

```bash
# 服务器本地
curl -I http://127.0.0.1:8081/crm
curl -I http://127.0.0.1:8082/crm
curl -I http://127.0.0.1/a          # 应该是 302 到 :8081/crm

# 外网（本地机器上跑）
curl -I http://<公网IP>:8081/crm
```

浏览器打开 `http://<公网IP>:8081/crm`，用 `Administrator` + 对应的
`ADMIN_PASSWORD` 登录。**登录后第一件事是改密码。**

再打开 F12 → Network → WS，确认 socket.io 连上了（状态 101 Switching
Protocols）。连不上说明 nginx 的 `/socket.io/` 段没生效。

---

## 云安全组（UCloud 外网防火墙）

服务器在 UCloud，公网访问由「外网防火墙」控制，跟系统里的 iptables/ufw 是两层。

进 UCloud 控制台 → **云主机 UHost → 外网防火墙 → 编辑规则**，改成：

| 协议 | 端口 | 源地址 | 动作 | 说明 |
|---|---|---|---|---|
| TCP | 22 | **你的办公网出口 IP/32** | 允许 | SSH，别开 0.0.0.0/0 |
| TCP | 80 | 0.0.0.0/0 | 允许 | `/a` `/b` 跳转入口 |
| TCP | 8081 | 0.0.0.0/0 | 允许 | 团队 A |
| TCP | 8082 | 0.0.0.0/0 | 允许 | 团队 B |
| TCP | 8000 | — | **删除/不要放行** | 容器端口，已绑 127.0.0.1 |
| TCP | 9000 | — | **删除/不要放行** | 同上 |
| TCP | 3306 | — | **不要放行** | 数据库 |

几个要点：

- **8000 / 9000 现在是放行状态的话，记得删掉规则。** 拉了新代码之后容器只绑
  `127.0.0.1`，外面本来也连不上，但规则留着没意义，属于多余的暴露面。
- 如果两个团队的办公网有固定出口 IP，**把 8081 / 8082 的源地址收窄到各自的
  IP 段**，比 0.0.0.0/0 安全得多，也顺便做了一层隔离。
- 22 端口强烈建议限源。现在是密码登录 + 弱密码，公网全开的话被爆破是迟早的事。
- UCloud 的防火墙规则是**白名单**：没写的端口默认拒绝，所以不用额外写 deny。

改完规则立即生效，不用重启主机。

> 服务器系统内没开 ufw（`ss -tlnp` 显示端口直接监听），所以只需要改云防火墙
> 这一层。如果以后启用了 ufw，记得同步放行 80/8081/8082。

---

## 日常运维

两套栈的命令只差 `-p` 和 `--env-file`。建议在 `~/.bashrc` 里加两个别名：

```bash
alias crma='sudo docker compose -p crm-a --env-file /youruicheng/crm/.env.a -f /youruicheng/crm/docker-compose.yml -f /youruicheng/crm/docker-compose.prod.yml'
alias crmb='sudo docker compose -p crm-b --env-file /youruicheng/crm/.env.b -f /youruicheng/crm/docker-compose.yml -f /youruicheng/crm/docker-compose.prod.yml'
```

之后：

```bash
crma ps                 # 看状态
crma logs -f frappe     # 看日志
crma restart frappe     # 重启
crma down               # 停（数据卷保留）
crma up -d              # 起
```

### 升级代码

```bash
cd /youruicheng/crm && sudo git pull
crma build              # 只 build 一次，两套共用镜像
crma up -d
crmb up -d
```

`entrypoint.sh` 每次启动会自动跑 `bench migrate`，不用手工执行。

建议先升 B（或者先升人少的那套）验证没问题，再升另一套。

### 备份

两套都要备。DB 和站点文件分开在各自的卷里：

```bash
for p in crm-a crm-b; do
  sudo docker run --rm -v ${p}_mariadb-data:/data -v /backup:/backup alpine \
    tar czf /backup/${p}-mariadb-$(date +%F).tgz -C /data .
  sudo docker run --rm -v ${p}_sites-data:/data -v /backup:/backup alpine \
    tar czf /backup/${p}-sites-$(date +%F).tgz -C /data .
done
```

或者用 bench 自带的（附件一起备）：

```bash
crma exec frappe bench --site crm-a.youruicheng.cn backup --with-files
```

建议挂个 cron 每天跑一次，再 rsync 到别的机器。现在服务器盘只剩 25G，备份别
堆在本地。

---

## 已知限制

- **纯 HTTP，没有 HTTPS。** 用 IP 访问拿不到受信任证书，登录密码是明文过网。
  内网/固定 IP 访问尚可接受，要上 HTTPS 就得有备案域名。
- **同一个浏览器不能同时登录两套。** 两套都在同一个 IP 上，session cookie 按
  域名隔离而不是按端口，会互相覆盖。两个团队是不同的人，一般没影响；同时要
  维护两套的管理员请用两个浏览器或无痕窗口。
- 磁盘 38G，第二套起来后要盯着点 `df -h`。

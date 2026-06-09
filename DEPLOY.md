# Zeabur + Supabase 部署指南

将 FastAPI 后端部署到公网，供 Android APK 通过 HTTPS 访问。

---

## 前置准备

| 账号 | 用途 |
|------|------|
| [GitHub](https://github.com) | 代码托管，Zeabur 拉取 |
| [Supabase](https://supabase.com) | PostgreSQL |
| [Zeabur](https://zeabur.com) | 运行 Docker 容器 |
| [NewsAPI](https://newsapi.org) | 新闻源（必填） |
| OpenAI / DeepSeek | LLM（可选，无则启发式） |

---

## 第一步：Supabase 建库

1. 登录 Supabase → **New project**
2. 记下数据库密码
3. 进入 **Project Settings → Database**

### 连接串（两个用途）

**运行时（App 查询）** — 推荐 **Session pooler**，端口 **5432**：

```text
postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:5432/postgres
```

**迁移（Alembic）** — 推荐 **Direct connection**，端口 **5432**：

```text
postgresql://postgres:[YOUR-PASSWORD]@db.[project-ref].supabase.co:5432/postgres
```

> 代码会自动把 `postgresql://` 转为 `postgresql+psycopg://` 并加上 `sslmode=require`。  
> 若迁移在 pooler 上报错，请设置单独的 `ALEMBIC_DATABASE_URL`（Direct）。

4. 可选：在 Supabase **SQL Editor** 执行 `SELECT 1` 确认项目已就绪

---

## 第二步：推送 backend 到 GitHub

Zeabur 从 Git 部署。建议 **单独仓库** 只包含 `backend/` 目录内容：

```bash
cd backend
git init
git add .
git commit -m "Prepare backend for Zeabur deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USER/portfolio-ai-api.git
git push -u origin main
```

若使用 monorepo，在 Zeabur 创建服务时把 **Root Directory** 设为 `backend`。

---

## 第三步：Zeabur 部署

1. 登录 [Zeabur Dashboard](https://dash.zeabur.com)
2. **Create Project** → 选择区域
3. **Add Service** → **Git** → 连接 GitHub → 选择仓库
4. Zeabur 会自动检测 `Dockerfile` 并用 Docker 构建
5. **Networking** → **Generate Domain**（获得 `https://xxx.zeabur.app`）

### 端口

- 容器内应用读取环境变量 **`PORT`**（Zeabur 自动注入）
- 本地 Docker Compose 未设置 `PORT` 时默认 **8000**
- 在 Zeabur 服务 **Ports** 中确认对外暴露端口与 `PORT` 一致

---

## 第四步：配置环境变量

在 Zeabur 服务页 → **Variables**，参考 `.env.production.example` 填写：

| 变量 | 说明 | 必填 |
|------|------|------|
| `DATABASE_URL` | Supabase Session pooler 连接串 | ✅ |
| `ALEMBIC_DATABASE_URL` | Supabase Direct 连接串（迁移用） | 推荐 |
| `ENVIRONMENT` | `production` | ✅ |
| `NEWS_API_KEY` | NewsAPI Key | ✅ |
| `RUN_MIGRATIONS` | `true`（首次部署跑表结构） | ✅ |
| `CACHE_BACKEND` | `memory`（MVP） | ✅ |
| `LLM_ENABLED` | `true` / `false` | ✅ |
| `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY` | LLM 密钥 | 若开 LLM |
| `UVICORN_WORKERS` | `1`（免费档） | 建议 |
| `CORS_ORIGINS` | `*`（MVP；仅移动端可保持） | 可选 |

保存后 Zeabur 会自动重新部署。

---

## 第五步：验收

将 `YOUR_DOMAIN` 替换为 Zeabur 分配的域名。

### 健康检查

```bash
curl https://YOUR_DOMAIN.zeabur.app/health
```

期望：

```json
{
  "status": "ok",
  "api": "ok",
  "database": "ok",
  "cache": "memory",
  "environment": "production"
}
```

### 核心接口

```bash
curl https://YOUR_DOMAIN.zeabur.app/portfolio

curl "https://YOUR_DOMAIN.zeabur.app/feed?symbols=BTC-USD&language=zh"

curl "https://YOUR_DOMAIN.zeabur.app/brief?symbols=BTC-USD&language=zh"
```

Feed / Brief 首次响应可能较慢（LLM），属正常现象。

---

## 第六步：Android APK 指向公网

```bash
cd ../portfolio_ai

flutter build apk --release \
  --dart-define=FEED_API_BASE_URL=https://YOUR_DOMAIN.zeabur.app
```

APK 路径：`build/app/outputs/flutter-apk/app-release.apk`

用 **4G/5G**（非同一 WiFi）安装测试，确认 Feed 能加载。

---

## 常见问题

### 部署一直 Deploying / 健康检查失败

- 查看 Zeabur **Logs**，常见原因：`DATABASE_URL` 错误、密码含特殊字符未 URL 编码
- 确认应用监听 `0.0.0.0:$PORT`（entrypoint 已处理）
- 首次启动含迁移，等待 30–60 秒

### `database: error`

- 检查 Supabase 项目是否暂停（免费档闲置会 sleep，Dashboard 点 Restore）
- 确认连接串密码正确，特殊字符需 [URL 编码](https://www.urlencoder.org/)
- 迁移失败时：设置 `ALEMBIC_DATABASE_URL` 为 **Direct** 连接

### Feed 空列表 / 500

- 确认 `NEWS_API_KEY` 已配置且未超免费额度
- 查看 Logs 中 NewsAPI 报错

### 国内访问慢

- Zeabur 节点可能在海外；MVP 可接受，后续可迁国内 VPS

---

## 本地对照（可选）

```bash
cd backend
cp .env.example .env
# 编辑 .env 填入 DATABASE_URL、NEWS_API_KEY

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Docker Compose（本地 PostgreSQL + Redis）：

```bash
docker compose up --build
```

---

## 下一步（P3+）

- [ ] Android Release 正式签名
- [ ] Supabase Auth + API JWT
- [ ] Upstash Redis（`CACHE_BACKEND=redis`）
- [ ] `PUT /portfolio` 持仓同步

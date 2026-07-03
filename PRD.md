# Fast EasiLogin 项目目录设计（PRD）

## 一、目标

### 设计目标

项目遵循以下原则：

1. 每个目录只负责一种职责（Single Responsibility）。
2. 业务代码与基础设施分离。
3. 前端源码与前端构建产物分离。
4. `uv run` 即可完成开发启动，不需要手动构建网页。
5. 后续增加模块无需调整整体目录。
6. 前端使用 pnpm 作为包管理器。
7. **不修改现有 API 逻辑**。

---

## 二、目录结构

```text
.
├── docs/                          # 文档
│
├── frontend/                      # Vite 前端源码（Git 管理）
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── pnpm-lock.yaml
│   └── vite.config.ts
│
├── fast_easilogin/                # Python Package
│   ├── __init__.py
│   ├── __main__.py                # 程序入口
│   │
│   ├── app/                       # 应用启动层
│   │   ├── __init__.py
│   │   ├── runner.py              # 程序真正入口
│   │   ├── bootstrap.py           # 启动初始化
│   │   └── mode.py                # 运行模式定义
│   │
│   ├── api/                       # HTTP API 层（保持现有结构）
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI 应用（现有）
│   │   ├── gateway/               # API 网关（现有）
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   └── state.py
│   │   └── user_auth/             # 用户认证（现有）
│   │       ├── __init__.py
│   │       ├── auth_service.py
│   │       └── user_service.py
│   │
│   ├── webui/                     # Python Web 服务层
│   │   ├── __init__.py
│   │   ├── app.py                 # FastAPI 应用（WebUI）
│   │   └── server.py              # Uvicorn 启动器
│   │
│   ├── storage/                   # 数据持久化层
│   │   ├── __init__.py
│   │   ├── config.py              # 配置管理
│   │   ├── kv_cache.py            # 键值缓存
│   │   ├── user_store.py          # 用户存储
│   │   └── models.py              # 数据模型
│   │
│   ├── core/                      # 基础设施层
│   │   ├── __init__.py
│   │   ├── constants.py           # 常量定义
│   │   ├── errors.py              # 错误定义
│   │   ├── http_client.py         # HTTP 客户端
│   │   ├── service_manager.py     # Windows 服务管理
│   │   └── basic_dir.py           # 目录定义
│   │
│   ├── runtime/                   # 运行时工具
│   │   ├── __init__.py
│   │   ├── service_runner.py      # 服务运行器
│   │   └── utils.py               # 运行时工具
│   │
│   └── assets/                    # 项目资源（包含前端构建产物）
│       ├── static/                # 构建后的前端产物（.gitignore）
│       │   ├── index.html
│       │   └── assets/
│       └── icon.ico
│
├── pyproject.toml
├── uv.lock
└── .gitignore
```

---

## 三、命令行参数设计

### 3.1 启动模式

```bash
# WebUI 模式（桌面双击）
uv run fast_easilogin --mode=webui

# 服务模式（后台运行）
uv run fast_easilogin --mode=service
```

### 3.2 服务安装（独立参数）

```bash
# 安装为 Windows 服务
uv run fast_easilogin --install-by-service

# 卸载 Windows 服务
uv run fast_easilogin --uninstall-service
```

### 3.3 参数组合

| 命令                   | 说明                                    |
| ---------------------- | --------------------------------------- |
| `--mode=webui`         | 启动 WebUI 模式（API + WebUI + 浏览器） |
| `--mode=service`       | 启动服务模式（仅 API）                  |
| `--install-by-service` | 安装为 Windows 服务（自动启动）         |
| `--uninstall-service`  | 卸载 Windows 服务                       |
| `--log-level=DEBUG`    | 设置日志级别                            |
| `--no-browser`         | WebUI 模式下不自动打开浏览器            |

### 3.4 运行模式定义

```python
# fast_easilogin/app/mode.py
from dataclasses import dataclass
from typing import Literal

@dataclass
class RunMode:
    mode: Literal["webui", "service"]  # 启动模式
    install_service: bool               # 是否安装服务
    uninstall_service: bool             # 是否卸载服务
    log_level: str                      # 日志级别
    access_log: bool                    # 是否启用访问日志
    no_browser: bool                    # 是否不打开浏览器
```

---

## 四、目录职责详解

### frontend/

整个 Vite 工程，使用 pnpm 作为包管理器。

```text
frontend/
├── src/               # 源码
├── public/            # 静态资源
├── package.json       # 依赖配置
├── pnpm-lock.yaml     # pnpm 锁文件
└── vite.config.ts     # Vite 配置
```

**规则：**

- 只有源码，永远不放 Python
- 使用 `pnpm install` 安装依赖
- 使用 `pnpm build` 构建产物
- 构建产物输出到 `fast_easilogin/assets/static/`

---

### fast_easilogin/app/

程序启动入口层。

| 文件           | 职责                            |
| -------------- | ------------------------------- |
| `runner.py`    | 程序真正入口，调用 `run()` 启动 |
| `bootstrap.py` | 启动初始化（目录、配置、日志）  |
| `mode.py`      | 运行模式定义（webui/service）   |

**禁止：** 业务逻辑

---

### fast_easilogin/api/

HTTP API 层（**保持现有结构，不修改**）。

| 文件/目录    | 职责                 |
| ------------ | -------------------- |
| `main.py`    | FastAPI 应用（现有） |
| `gateway/`   | API 网关（现有）     |
| `user_auth/` | 用户认证（现有）     |

**重要：** 保持现有 API 逻辑不变，只做必要的重构以支持新的目录结构。

---

### fast_easilogin/webui/

Python Web 服务层（提供前端静态文件）。

| 文件        | 职责                         |
| ----------- | ---------------------------- |
| `app.py`    | FastAPI 应用（静态文件服务） |
| `server.py` | Uvicorn 启动器               |

**注意：** 静态文件位于 `fast_easilogin/assets/static/`，不在 `webui/` 目录下。

---

### fast_easilogin/storage/

数据持久化层。

| 文件            | 职责         |
| --------------- | ------------ |
| `config.py`     | 配置文件读写 |
| `kv_cache.py`   | 键值缓存     |
| `user_store.py` | 用户数据存储 |
| `models.py`     | 数据模型定义 |

**扩展：** 未来支持 SQLite、Redis、Memory 统一放这里。

---

### fast_easilogin/core/

基础设施层。

| 文件                 | 职责             |
| -------------------- | ---------------- |
| `constants.py`       | 常量定义         |
| `errors.py`          | 错误定义         |
| `http_client.py`     | HTTP 客户端封装  |
| `service_manager.py` | Windows 服务管理 |
| `basic_dir.py`       | 目录路径定义     |

**禁止：** 业务逻辑。

---

### fast_easilogin/runtime/

运行时工具。

| 文件                | 职责                      |
| ------------------- | ------------------------- |
| `service_runner.py` | 服务运行器（API + WebUI） |
| `utils.py`          | 日志、事件循环等工具      |

---

### fast_easilogin/assets/

项目资源和构建产物。

| 文件/目录           | 职责                           |
| ------------------- | ------------------------------ |
| `static/`           | 构建后的前端产物（.gitignore） |
| `static/index.html` | 前端入口                       |
| `static/assets/`    | 前端资源（JS、CSS）            |
| `icon.ico`          | 应用图标                       |

**规则：**

- `static/` 目录由 `pnpm build` 自动生成
- 禁止手动修改
- 加入 `.gitignore`

---

## 五、数据流向

### 5.1 WebUI 模式启动流程

```text
uv run fast_easilogin --mode=webui
    │
    ▼
┌─────────────┐
│  Bootstrap  │  ← 初始化目录、配置、日志
└─────────────┘
    │
    ▼
┌─────────────┐
│  Start API  │  ← 启动 API 服务（端口 24300）
└─────────────┘
    │
    ▼
┌──────────────┐
│  Start WebUI │  ← 启动 WebUI 服务（端口 3000）
└──────────────┘
    │
    ▼
┌──────────────┐
│ Open Browser │  ← 自动打开浏览器
└──────────────┘
    │
    ▼
  等待信号
```

### 5.2 服务模式启动流程

```text
uv run fast_easilogin --mode=service
    │
    ▼
┌─────────────┐
│  Bootstrap  │  ← 初始化目录、配置、日志
└─────────────┘
    │
    ▼
┌─────────────┐
│  Start API  │  ← 启动 API 服务（端口 24300）
└─────────────┘
    │
    ▼
  等待信号
```

### 5.3 服务安装流程

```text
uv run fast_easilogin --install-by-service
    │
    ▼
┌─────────────────┐
│ Install Service │  ← 注册 Windows 服务
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  Start Service  │  ← 启动服务
└─────────────────┘
    │
    ▼
  完成
```

### 5.4 请求处理流程

```
HTTP Request
    │
    ▼
┌─────────────┐
│   Gateway   │  ← 认证、日志、错误处理
└─────────────┘
    │
    ▼
┌─────────────┐
│   Router    │  ← 路由分发
└─────────────┘
    │
    ▼
┌─────────────┐
│   Service   │  ← 业务逻辑
└─────────────┘
    │
    ▼
┌─────────────┐
│  Repository │  ← 数据访问
└─────────────┘
    │
    ▼
┌─────────────┐
│   Storage   │  ← 持久化
└─────────────┘
```

---

## 七、配置文件格式

### 7.1 配置文件位置

```text
fast_easilogin/data/appsettings.toml
```

### 7.2 配置文件结构

```toml
[Global]
port = 24300              # API 端口
webui_port = 3000         # WebUI 端口
enable_eventlog = true    # 启用 Windows 事件日志

[Logging]
file_level = "INFO"       # 文件日志级别
console_level = "DEBUG"   # 控制台日志级别

[Cache]
max_entries = 512         # 最大缓存条目
ttl_seconds = 3600        # 缓存过期时间
```

---

## 八、Git 管理

### 8.1 Git 管理

```text
frontend/          # 前端源码
fast_easilogin/    # Python 源码（除 assets/static/）
docs/              # 文档
```

### 8.2 Git 忽略

```gitignore
# 前端构建产物
fast_easilogin/assets/static/

# 前端依赖
frontend/node_modules/

# Python
__pycache__/
*.pyc
.venv/
```

---

## 九、迁移指南

### 9.1 从当前结构迁移

| 当前位置         | 迁移到              | 说明          |
| ---------------- | ------------------- | ------------- |
| `api/main.py`    | `api/main.py`       | **保持不变**  |
| `api/gateway/`   | `api/gateway/`      | **保持不变**  |
| `api/user_auth/` | `api/user_auth/`    | **保持不变**  |
| `api/static/`    | `assets/static/`    | 静态文件移动  |
| `shared/store/`  | `storage/`          | 数据存储      |
| `shared/*.py`    | `core/`             | 基础设施      |
| `runtime/`       | `runtime/` + `app/` | 运行时 + 启动 |
| `webui/`         | `webui/`            | 保持不变      |

### 9.2 迁移原则

1. **不修改现有 API 逻辑**
2. 只做目录结构调整
3. 更新导入路径
4. 测试所有功能

---

## 十、设计原则

1. **单一职责**：一个目录只有一种职责。
2. **分层架构**：API → Auth → Storage，单向依赖。
3. **前后端分离**：前端源码与构建产物完全分离。
4. **基础设施独立**：Core 不依赖业务代码。
5. **工具函数独立**：Utils 不依赖项目模块。
6. **静态产物自动生成**：Static 永远由 Build 自动生成。
7. **可扩展性**：新增业务模块时，仅增加对应目录，不修改整体结构。
8. **统一命名**：所有目录命名采用行业通用名称，降低理解成本。
9. **保持兼容**：不修改现有 API 逻辑，确保向后兼容。

---

## 十一、技术栈

| 层级 | 技术                             |
| ---- | -------------------------------- |
| 前端 | React + Vite + pnpm              |
| 后端 | Python 3.11+ + FastAPI + Uvicorn |
| 数据 | TOML 配置 + JSON 缓存            |
| 服务 | pywin32 (Windows Service)        |

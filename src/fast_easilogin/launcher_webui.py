#!/usr/bin/env python
"""
希沃快捷登录 WebUI 启动脚本

功能:
  - 配置 hosts 文件映射
  - 安装/卸载 Windows 服务
  - 启动 WebUI 服务 (独立于 API 服务)

用法:
  python -m fast_easilogin.launcher_webui [选项]

选项:
  --install       安装为 Windows 服务
  --uninstall     卸载 Windows 服务
  --no-elevate    不自动请求管理员权限
  --help          显示帮助信息
"""

from __future__ import annotations

import argparse
import asyncio
import os
import platform
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from loguru import logger

HOSTS_ENTRY = "local.id.seewo.com"
HOSTS_IP = "127.0.0.1"
SERVICE_NAME = "SeewoFastLoginService"

STATIC_DIR = Path(__file__).parent / "webui" / "static"


def is_admin() -> bool:
    if platform.system() != "Windows":
        return True
    try:
        import ctypes

        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run_as_admin(args: list[str] | None = None) -> bool:
    if platform.system() != "Windows":
        return False

    try:
        import ctypes

        if args is None:
            args = sys.argv[1:]

        script = sys.argv[0]
        params = " ".join(args)

        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            f'"{script}" {params}',
            None,
            1,
        )
        return True
    except Exception:
        return False


def check_hosts_entry() -> bool:
    hosts_path = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"
    if not hosts_path.exists():
        return False
    try:
        content = hosts_path.read_text(encoding="utf-8", errors="ignore")
        return HOSTS_ENTRY in content
    except Exception:
        return False


def add_hosts_entry() -> bool:
    if check_hosts_entry():
        print(f"[√] hosts 映射已存在: {HOSTS_IP}    {HOSTS_ENTRY}")
        return True

    hosts_path = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"
    try:
        print(f"[*] 正在添加 hosts 映射...")
        with open(hosts_path, "a", encoding="utf-8") as f:
            f.write(f"\n{HOSTS_IP}    {HOSTS_ENTRY}\n")
        print(f"[√] hosts 映射已添加: {HOSTS_IP}    {HOSTS_ENTRY}")
        return True
    except PermissionError:
        print("[×] 权限不足，无法修改 hosts 文件")
        print("    请以管理员身份运行此脚本")
        return False
    except Exception as e:
        print(f"[×] 添加 hosts 映射失败: {e}")
        return False


def install_service() -> bool:
    print("[*] 正在安装 Windows 服务...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "fast_easilogin", "--services", "install"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"[√] Windows 服务安装完成")
            print(f"    可通过 'sc query {SERVICE_NAME}' 查看服务状态")
            return True
        else:
            print(f"[×] 安装服务失败: {result.stderr or result.stdout}")
            return False
    except Exception as e:
        print(f"[×] 安装服务失败: {e}")
        return False


def uninstall_service() -> bool:
    print("[*] 正在卸载 Windows 服务...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "fast_easilogin", "--services", "uninstall"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"[√] Windows 服务卸载完成")
            return True
        else:
            print(f"[×] 卸载服务失败: {result.stderr or result.stdout}")
            return False
    except Exception as e:
        print(f"[×] 卸载服务失败: {e}")
        return False


def get_ports() -> tuple[int, int]:
    api_port = 24300
    webui_port = 24301
    try:
        from fast_easilogin.shared.store.config import load_appsettings_model

        settings = load_appsettings_model()
        api_port = int(settings.Global.port)
        webui_port = int(getattr(settings.Global, "webui_port", 24301))
    except Exception:
        pass
    return api_port, webui_port


def create_webui_app(*, api_port: int = 24300, webui_port: int = 24301) -> FastAPI:
    api_base = f"http://127.0.0.1:{api_port}"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.success(f"WebUI 启动成功: http://127.0.0.1:{webui_port}/")
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.get(f"{api_base}/")
                logger.success(f"API 服务已连接: {api_base}")
        except httpx.ConnectError:
            logger.warning(f"API 服务未运行: {api_base} (请先启动 API 服务)")
        except Exception as e:
            logger.warning(f"API 服务连接异常: {api_base} ({e})")
        yield

    app = FastAPI(default_response_class=JSONResponse, lifespan=lifespan)

    @app.middleware("http")
    async def add_cors_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE,PUT,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.get("/", response_class=HTMLResponse)
    async def redirect_to_webui():
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/webui/")

    @app.get("/webui/", response_class=HTMLResponse)
    async def webui_index():
        index_path = STATIC_DIR / "index.html"
        if not index_path.exists():
            return HTMLResponse(content="<h1>WebUI not found</h1>", status_code=404)
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    from fast_easilogin.webui.router import router as webui_router

    app.include_router(webui_router, prefix="/webui")

    http_client = httpx.AsyncClient(base_url=api_base, timeout=30.0)

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    async def proxy_api(request: Request, path: str):
        if request.method == "OPTIONS":
            return Response(status_code=200)

        url = f"/{path}"
        if request.url.query:
            url += f"?{request.url.query}"

        body = await request.body()

        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("content-length", None)

        try:
            response = await http_client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
            )
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        except httpx.ConnectError:
            return JSONResponse(
                content={"message": "API 服务未响应，请确保 API 服务已启动", "statusCode": "503"},
                status_code=503,
            )
        except Exception as e:
            logger.exception(f"代理请求失败: {e}")
            return JSONResponse(
                content={"message": str(e), "statusCode": "500"},
                status_code=500,
            )

    return app


def start_webui() -> None:
    api_port, webui_port = get_ports()

    print()
    print("=" * 50)
    print("  希沃快捷登录 WebUI")
    print("=" * 50)
    print()
    print(f"  API 地址: http://127.0.0.1:{api_port}")
    print(f"  WebUI 地址: http://127.0.0.1:{webui_port}/")
    print()
    print("  按 Ctrl+C 停止服务")
    print()

    app = create_webui_app(api_port=api_port, webui_port=webui_port)

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=webui_port,
        server_header=False,
        access_log=False,
        log_config=None,
    )
    server = uvicorn.Server(config)
    server.run()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="希沃快捷登录 WebUI 启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--install", action="store_true", help="安装为 Windows 服务")
    parser.add_argument("--uninstall", action="store_true", help="卸载 Windows 服务")
    parser.add_argument("--no-elevate", action="store_true", help="不自动请求管理员权限")

    args = parser.parse_args()

    if args.install and args.uninstall:
        print("[×] 错误: 不能同时指定 --install 和 --uninstall")
        sys.exit(1)

    need_admin = args.install or args.uninstall or not check_hosts_entry()

    if not is_admin() and need_admin and not args.no_elevate:
        print("[*] 需要管理员权限，正在请求...")
        elevate_args = [arg for arg in sys.argv[1:] if arg != "--no-elevate"]
        if run_as_admin(elevate_args):
            sys.exit(0)
        else:
            print("[×] 无法获取管理员权限，继续以普通模式运行")
            print()

    print()
    print("=" * 50)
    print("  希沃快捷登录 WebUI 启动器")
    print("=" * 50)
    print()

    if not is_admin():
        print("[!] 警告: 未以管理员身份运行")
        print("    请以管理员身份运行此脚本以:")
        print("    - 自动配置 hosts 映射")
        print("    - 安装/卸载 Windows 服务")
        print()

    if args.install:
        if is_admin():
            add_hosts_entry()
            print()
        install_service()
        return

    if args.uninstall:
        uninstall_service()
        return

    if is_admin():
        add_hosts_entry()
        print()
    else:
        if not check_hosts_entry():
            print("[!] hosts 映射未配置，服务可能无法正常工作")
            print("    请以管理员身份运行以自动配置")
            print()

    print("[*] 提示: 使用 --install 可安装为 Windows 服务")
    print("          使用 --uninstall 可卸载 Windows 服务")
    print()

    start_webui()


if __name__ == "__main__":
    main()

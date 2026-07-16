# scripts/13_01_compose_demo.py
"""13.01 容器化编排验收（离线优先）。

【本课要感受的三件事】
1. 仓库里有可提交的 Dockerfile + docker-compose.yml
2. health 契约：GET /health → status=ok（本机或容器）
3. 密钥不进镜像；stop_grace_period / SIGTERM 有配置

有 Docker 时额外跑：docker compose config / up（可选 LIVE_COMPOSE=1）
无 Docker 时：校验文件 + 本机 /health（若 8091 已起）即可 PASS。

工作目录：必须在 ai-service/ 下。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

NOTE_PATH = ROOT / "notes" / "compose_result.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def check_files() -> dict:
    """文件与关键配置是否齐全。"""
    df = ROOT / "Dockerfile"
    dc = ROOT / "docker-compose.yml"
    di = ROOT / ".dockerignore"
    life = ROOT / "app" / "lifecycle.py"
    text_dc = _read(dc)
    text_df = _read(df)
    ok = (
        df.is_file()
        and dc.is_file()
        and di.is_file()
        and life.is_file()
        and "healthcheck" in text_dc
        and "stop_grace_period" in text_dc
        and "INTERNAL_TOKEN" in text_dc
        and ".env" in _read(di)
        and "timeout-graceful-shutdown" in text_df
        and "curl" in text_df
    )
    return {
        "ok": ok,
        "dockerfile": df.is_file(),
        "compose": dc.is_file(),
        "dockerignore": di.is_file(),
        "lifecycle": life.is_file(),
        "has_healthcheck": "healthcheck" in text_dc,
        "has_grace": "stop_grace_period" in text_dc,
        "dockerignore_skips_env": ".env" in _read(di),
    }


def check_compose_yaml() -> dict:
    """用 PyYAML 解析 compose（不依赖 docker 二进制）。"""
    import yaml

    raw = _read(ROOT / "docker-compose.yml")
    data = yaml.safe_load(raw) or {}
    services = data.get("services") or {}
    svc = services.get("ai-service") or {}
    hc = svc.get("healthcheck") or {}
    ok = bool(svc.get("build") is not None or svc.get("image")) and bool(hc)
    return {
        "ok": ok,
        "service_keys": list(services.keys()),
        "ports": svc.get("ports"),
        "healthcheck_test": hc.get("test"),
        "stop_grace_period": svc.get("stop_grace_period"),
    }


def check_local_health() -> dict:
    """若本机已有进程在听 8091，则探活。"""
    import httpx

    base = os.getenv("AI_BASE", "http://127.0.0.1:8091").rstrip("/")
    try:
        r = httpx.get(f"{base}/health", timeout=2.0)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        return {
            "reachable": r.status_code == 200,
            "status_code": r.status_code,
            "body": body,
            "ok": r.status_code == 200 and body.get("status") == "ok",
        }
    except Exception as exc:  # noqa: BLE001
        return {"reachable": False, "ok": False, "error": str(exc)}


def check_docker_cli() -> dict:
    """探测 docker / compose 是否可用。"""
    docker = shutil.which("docker")
    if not docker:
        return {"available": False, "ok": True, "skip": "docker not installed"}
    try:
        ver = subprocess.run(
            [docker, "compose", "version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        cfg = subprocess.run(
            [docker, "compose", "config"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return {
            "available": True,
            "version_ok": ver.returncode == 0,
            "config_ok": cfg.returncode == 0,
            "ok": ver.returncode == 0 and cfg.returncode == 0,
            "config_stderr": (cfg.stderr or "")[:300],
        }
    except Exception as exc:  # noqa: BLE001
        return {"available": True, "ok": False, "error": str(exc)}


def try_live_compose() -> dict:
    """LIVE_COMPOSE=1 时真 up + health + down（需本机有 Docker）。"""
    if os.getenv("LIVE_COMPOSE", "").strip() != "1":
        return {"skipped": True, "ok": True}
    docker = shutil.which("docker")
    if not docker:
        return {"skipped": True, "ok": True, "reason": "no docker"}
    steps = []
    try:
        up = subprocess.run(
            [docker, "compose", "up", "-d", "--build"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        steps.append({"up": up.returncode})
        if up.returncode != 0:
            return {"skipped": False, "ok": False, "steps": steps, "stderr": up.stderr[-500:]}
        import time

        import httpx

        healthy = False
        for _ in range(30):
            time.sleep(2)
            try:
                r = httpx.get("http://127.0.0.1:8091/health", timeout=2.0)
                if r.status_code == 200 and r.json().get("status") == "ok":
                    healthy = True
                    break
            except Exception:  # noqa: BLE001
                continue
        steps.append({"health": healthy})
        down = subprocess.run(
            [docker, "compose", "down"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        steps.append({"down": down.returncode})
        return {"skipped": False, "ok": healthy and down.returncode == 0, "steps": steps}
    except Exception as exc:  # noqa: BLE001
        subprocess.run([docker, "compose", "down"], cwd=ROOT, check=False)
        return {"skipped": False, "ok": False, "error": str(exc)}


def main() -> None:
    print("=" * 52, "13.01 compose")
    print("\n" + "=" * 52, "STEP 1 · 文件与密钥边界")
    files = check_files()
    print(files)
    assert files["ok"], files

    print("\n" + "=" * 52, "STEP 2 · 解析 docker-compose.yml")
    yml = check_compose_yaml()
    print(yml)
    assert yml["ok"], yml

    print("\n" + "=" * 52, "STEP 3 · Docker CLI（可选）")
    dock = check_docker_cli()
    print(dock)
    assert dock["ok"], dock

    print("\n" + "=" * 52, "STEP 4 · 本机 /health（可选）")
    health = check_local_health()
    print(health)

    print("\n" + "=" * 52, "STEP 5 · LIVE_COMPOSE（可选）")
    live = try_live_compose()
    print(live)
    assert live["ok"], live

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text(
        "\n".join(
            [
                "# 13.01 容器化编排 · 验收笔记",
                "",
                "## 文件检查",
                f"- Dockerfile / compose / .dockerignore / lifecycle：`{files['ok']}`",
                f"- healthcheck：`{files['has_healthcheck']}`；stop_grace_period：`{files['has_grace']}`",
                f"- .dockerignore 排除 .env：`{files['dockerignore_skips_env']}`",
                "",
                "## Compose 服务",
                f"- services：`{yml['service_keys']}`",
                f"- ports：`{yml['ports']}`",
                f"- grace：`{yml['stop_grace_period']}`",
                "",
                "## Docker",
                f"- available：`{dock.get('available')}` config_ok=`{dock.get('config_ok', dock.get('skip'))}`",
                "",
                "## Health",
                f"- reachable：`{health.get('reachable')}` body=`{health.get('body')}`",
                "",
                "## 常用命令",
                "```bash",
                "cd ai-service",
                "docker compose up -d --build",
                "curl -f http://127.0.0.1:8091/health",
                "docker compose down",
                "```",
                "",
                "密钥：只放 `.env`，已在 `.dockerignore` 排除；不要 COPY 进镜像。",
                "",
                "SUMMARY: compose 验收通过（无 Docker 时以文件+YAML 为准）",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print("\nNOTE →", NOTE_PATH)
    print("SUMMARY: 13.01 验收通过")


if __name__ == "__main__":
    main()

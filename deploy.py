#!/usr/bin/env python3
"""Deploy checker to prod server.

Usage:
    python deploy.py                    # rebuild + up all services
    python deploy.py bot                # rebuild + restart only bot
    python deploy.py bot miniapp        # rebuild + restart bot and miniapp
    python deploy.py --recreate         # down then up (loses in-memory state)
    python deploy.py --logs             # tail logs of all services
    python deploy.py --logs bot         # tail logs of specific service
    python deploy.py --ps               # show services status
    python deploy.py --shell            # open interactive shell command

Reads credentials from environment or tmp/deploy.env:
    DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASSWORD, DEPLOY_PATH
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.resolve()


def load_env() -> dict[str, str]:
    env_file = ROOT / "tmp" / "deploy.env"
    values: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()
    for k in ("DEPLOY_HOST", "DEPLOY_USER", "DEPLOY_PASSWORD", "DEPLOY_PATH"):
        if os.environ.get(k):
            values[k] = os.environ[k]
    return values


def connect():
    try:
        import paramiko
    except ImportError:
        raise SystemExit("paramiko not installed: pip install paramiko")

    env = load_env()
    host = env.get("DEPLOY_HOST")
    user = env.get("DEPLOY_USER", "root")
    password = env.get("DEPLOY_PASSWORD")
    remote_path = env.get("DEPLOY_PATH", "/opt/max-checker")
    if not host or not password:
        raise SystemExit(
            "Missing credentials. Set DEPLOY_HOST + DEPLOY_PASSWORD in env or tmp/deploy.env"
        )

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username=user, password=password, timeout=15)
    c.get_transport().set_keepalive(30)
    return c, remote_path


def compose_prefix(remote_path: str) -> str:
    return (
        f"docker compose -f {remote_path}/docker-compose.yml "
        f"-f {remote_path}/docker-compose.prod.yml --project-directory {remote_path}"
    )


def package_project() -> Path:
    tarball = Path(tempfile.gettempdir()) / "max-checker.tar.gz"
    excludes = [
        "./node_modules",
        "**/node_modules",
        "**/dist",
        "**/build",
        "**/__pycache__",
        "**/.venv",
        "**/venv",
        "./tmp",
        "./storage",
        "./.env",
        "./.git",
        "./.github",
    ]
    cmd = ["tar", "-czf", str(tarball).replace("\\", "/")]
    for e in excludes:
        cmd += ["--exclude", e]
    cmd.append(".")
    print(f"[pack] {tarball}")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
        raise SystemExit("tar failed")
    print(f"[pack] {tarball.stat().st_size} bytes")
    return tarball


def deploy(services: list[str], recreate: bool) -> None:
    tarball = package_project()
    c, remote_path = connect()

    print("[sftp] uploading tarball")
    sftp = c.open_sftp()
    sftp.put(str(tarball), "/tmp/max-checker.tar.gz")
    sftp.close()

    compose = compose_prefix(remote_path)
    services_arg = " ".join(services) if services else ""

    steps: list[tuple[str, str, int]] = [
        ("extract", f"mkdir -p {remote_path} && tar -xzf /tmp/max-checker.tar.gz -C {remote_path}", 60),
        ("build", f"cd {remote_path} && {compose} build {services_arg} 2>&1 | tail -5", 600),
    ]
    if recreate:
        steps.append(("down", f"{compose} down {services_arg}", 60))
    steps.append(("up", f"{compose} up -d {services_arg} 2>&1", 90))

    for name, cmd, timeout in steps:
        print(f"[{name}] running")
        stdin, stdout, _ = c.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        if out.strip():
            print(out.strip())
        if exit_code != 0:
            print(f"[{name}] EXIT {exit_code}")
            raise SystemExit(1)

    print("[status]")
    stdin, stdout, _ = c.exec_command(f"{compose} ps", timeout=15)
    print(stdout.read().decode(errors="replace"))

    print("[health]")
    try:
        stdin, stdout, _ = c.exec_command(
            "curl -sf --max-time 5 https://max.nc-group.space/api/health",
            timeout=30,
        )
        out = stdout.read().decode(errors="replace")
        print(out.strip() or "(no response)")
    except Exception as e:
        print(f"health check skipped: {e}")

    c.close()
    print("[done]")


def logs(services: list[str], follow: bool = True) -> None:
    c, remote_path = connect()
    compose = compose_prefix(remote_path)
    services_arg = " ".join(services) if services else ""
    flag = "-f --tail=100" if follow else "--tail=200"
    cmd = f"{compose} logs {flag} {services_arg}"
    print(f"[logs] {'streaming' if follow else 'tail'} {services_arg or 'all'} (Ctrl+C to stop)")
    stdin, stdout, _ = c.exec_command(cmd, get_pty=True, timeout=None)
    try:
        for line in iter(stdout.readline, ""):
            if not line:
                break
            print(line.rstrip())
    except KeyboardInterrupt:
        pass
    finally:
        c.close()


def ps() -> None:
    c, remote_path = connect()
    stdin, stdout, _ = c.exec_command(f"{compose_prefix(remote_path)} ps", timeout=15)
    print(stdout.read().decode(errors="replace"))
    c.close()


def main() -> None:
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print(__doc__)
        return

    mode = "deploy"
    for m in ("--logs", "--ps", "--shell"):
        if m in args:
            mode = m.lstrip("-")
            args.remove(m)
            break

    recreate = False
    if "--recreate" in args:
        recreate = True
        args.remove("--recreate")

    if mode == "logs":
        logs(services=args, follow=True)
    elif mode == "ps":
        ps()
    else:
        deploy(services=args, recreate=recreate)


if __name__ == "__main__":
    main()

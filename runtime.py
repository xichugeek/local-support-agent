"""Prepare pinned official dependencies or launch the local tutorial."""

import argparse
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import time
import webbrowser
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zipfile import ZipFile

from server import LOCAL, ROOT, serve

RUNTIME = "llama-b12588-bin-win-cpu-x64.zip"
WEIGHTS = "Qwen3-1.7B-Q8_0.gguf"
FILES = {
    RUNTIME: ("https://github.com/ggml-org/llama.cpp/releases/download/b12588/" + RUNTIME,
              "e61b81d5e11f49edc88c00aa7513291e0be6a341ff8498083f775ee721568be4"),
    WEIGHTS: ("https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/90862c4b9d2787eaed51d12237eafdfe7c5f6077/" + WEIGHTS,
              "061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a"),
}


def sha(path):
    with path.open("rb") as data:
        return hashlib.file_digest(data, "sha256").hexdigest()


def acquire(folder, name, source):
    url, expected = FILES[name]
    target = folder / name
    if target.exists():
        if sha(target) != expected:
            raise ValueError(f"{target.name} SHA-256 不符。请移走这份文件，再运行准备。")
        return target
    partial = target.with_suffix(target.suffix + ".part")
    print(f"准备 {name}", flush=True)
    try:
        if source:
            shutil.copyfile(source / name, partial)
        else:
            request = Request(url, headers={"User-Agent": "XichuGeek-SupportDesk-Lab/1.0"})
            with urlopen(request, timeout=90) as data, partial.open("wb") as out:
                if urlparse(data.geturl()).scheme != "https":
                    raise ValueError("下载地址必须使用 HTTPS")
                downloaded = 0
                while chunk := data.read(1024 * 1024):
                    out.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (128 * 1024 * 1024) == 0:
                        print(f"已下载 {downloaded // (1024 * 1024)} MB", flush=True)
        if sha(partial) != expected:
            raise ValueError(f"{name} SHA-256 不符")
        partial.rename(target)
    finally:
        partial.unlink(missing_ok=True)
    return target


def prepare(folder, source=None):
    folder.mkdir(parents=True, exist_ok=True)
    archive = acquire(folder, RUNTIME, source)
    acquire(folder, WEIGHTS, source)
    destination = folder / "llama-b12588"
    marker = destination / "runtime-receipt.json"
    if destination.exists():
        if not marker.is_file():
            raise ValueError("存在未登记的运行器目录，请先移走它。")
        print("已核对官方下载文件，可运行 start.cmd。", flush=True)
        return
    with TemporaryDirectory(prefix="unpack-", dir=folder) as temporary:
        target = Path(temporary) / "ready"
        target.mkdir()
        with ZipFile(archive) as zipped:
            for member in zipped.infolist():
                parts = PurePosixPath(member.filename).parts
                if not parts or any(part in (".", "..", "/") or ":" in part or "\\" in part for part in parts):
                    raise ValueError("运行器压缩包包含不安全路径")
                zipped.extract(member, target)
        files = list(target.rglob("llama-server.exe"))
        if len(files) != 1:
            raise ValueError("官方包中未找到唯一的 llama-server.exe")
        actual = files[0].parent
        receipt = {"archive_sha256": FILES[RUNTIME][1], "server_sha256": sha(files[0])}
        (actual / marker.name).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        actual.rename(destination)
    print("运行器与模型已准备完成，可运行 start.cmd。", flush=True)


def start(folder, db, open_tab):
    binary = folder / "llama-b12588" / "llama-server.exe"
    model = folder / WEIGHTS
    receipt = binary.with_name("runtime-receipt.json")
    if not (binary.is_file() and model.is_file() and receipt.is_file()):
        raise ValueError("请先双击 prepare-runtime.cmd，完成运行器和模型准备。")
    if sha(binary) != json.loads(receipt.read_text(encoding="utf-8"))["server_sha256"]:
        raise ValueError("运行器文件校验失败。")
    for port in (18767, 18768):
        with socket.socket() as probe:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as error:
                raise ValueError(f"端口 {port} 不可用。请先关闭已经启动的同一演示。") from error
    token = secrets.token_urlsafe(24)
    log = folder / "model.log"
    print("正在加载本地 Qwen3-1.7B。", flush=True)
    with log.open("wb") as diagnostic:
        backend = subprocess.Popen([
            str(binary), "-m", str(model), "--host", "127.0.0.1", "--port", "18767", "--alias", "qwen3-1.7b",
            "--no-ui", "--reasoning", "off", "-c", "2048", "-np", "1", "-t", "4", "-ngl", "0", "--api-key", token,
        ], cwd=binary.parent, stdout=diagnostic, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and backend.poll() is None:
                try:
                    request = Request("http://127.0.0.1:18767/health", headers={"Authorization": f"Bearer {token}"})
                    with LOCAL.open(request, timeout=1) as health:
                        if json.load(health).get("status") == "ok":
                            break
                except OSError:
                    time.sleep(.3)
            else:
                raise RuntimeError("模型未启动，请查看 runtime/model.log。")
            when_ready = (lambda port: webbrowser.open(f"http://127.0.0.1:{port}/")) if open_tab else None
            serve(db, token=token, on_ready=when_ready)
        finally:
            if backend.poll() is None:
                backend.terminate()
                backend.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "start"))
    parser.add_argument("--folder", type=Path, default=ROOT / "runtime")
    parser.add_argument("--from-cache", type=Path, help="目录内需有两份官方同名文件")
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "support.sqlite3")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    try:
        if os.name != "nt":
            raise ValueError("当前安装流程适用于 Windows x64。")
        if args.action == "prepare":
            prepare(args.folder.resolve(), args.from_cache)
        else:
            start(args.folder.resolve(), args.db, not args.no_browser)
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"启动或准备失败：{error}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

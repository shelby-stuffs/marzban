from __future__ import annotations

import atexit
import hashlib
import json
import os
import signal
import subprocess
import time
import tempfile
import threading
from collections import deque
from pathlib import Path


class SingBoxCore:
    def __init__(self, executable_path: str, config_path: str):
        self.executable_path = executable_path
        self.config_path = Path(config_path)
        self.process = None
        self._digest = None
        self._lock = threading.RLock()
        self.logs = deque(maxlen=500)
        atexit.register(self.stop)

    @property
    def started(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def version(self) -> str:
        return subprocess.check_output([self.executable_path, "version"], stderr=subprocess.STDOUT, text=True).splitlines()[0]

    def _capture_logs(self):
        while self.process and self.process.stdout:
            line = self.process.stdout.readline()
            if line:
                self.logs.append(line.rstrip())
            elif self.process.poll() is not None:
                break

    def _validate_file(self, path: str) -> None:
        self.logs.append(f"[marzban] validating config: {path}")
        result = subprocess.run([self.executable_path, "check", "-c", path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        if result.stdout.strip():
            self.logs.extend(result.stdout.strip().splitlines())
        if result.returncode:
            raise ValueError(f"Invalid sing-box config: {result.stdout.strip()}")

    def _start_existing(self) -> None:
        if self.started:
            return
        self.logs.append(f"[marzban] starting: {self.executable_path} run -c {self.config_path}")
        self.process = subprocess.Popen([self.executable_path, "run", "-c", str(self.config_path)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.logs.append(f"[marzban] sing-box started, pid={self.process.pid}")
        threading.Thread(target=self._capture_logs, daemon=True).start()

    def validate(self, config: dict) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".marzban-sing-box-check-", suffix=".json.tmp", dir=self.config_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(config, file, indent=2)
                file.write("\n")
            self._validate_file(temporary)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def _config_digest(config: dict) -> str:
        payload = json.dumps(config, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def _write_validated(self, config: dict) -> bytes | None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        previous = self.config_path.read_bytes() if self.config_path.exists() else None
        fd, temporary = tempfile.mkstemp(prefix=".marzban-sing-box-", suffix=".json.tmp", dir=self.config_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(config, file, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            self._validate_file(temporary)
            os.replace(temporary, self.config_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return previous

    def _restore(self, previous: bytes | None) -> None:
        if previous is None:
            self.config_path.unlink(missing_ok=True)
            return
        temporary = self.config_path.with_name(f".{self.config_path.name}.rollback.tmp")
        temporary.write_bytes(previous)
        os.replace(temporary, self.config_path)

    def _signal_reload(self) -> None:
        process = self.process
        if process is None or process.poll() is not None:
            self._start_existing()
            return
        pid = process.pid
        self.logs.append(f"[marzban] hot reload requested, pid={pid}")
        process.send_signal(signal.SIGHUP)
        time.sleep(0.15)
        if process.poll() is not None:
            raise RuntimeError(f"sing-box exited during hot reload, pid={pid}")
        self.logs.append(f"[marzban] hot reload accepted, pid={pid}")

    def apply(self, config: dict, *, force_reload: bool = False) -> bool:
        digest = self._config_digest(config)
        with self._lock:
            if digest == self._digest and self.started and not force_reload:
                return False
            previous_digest = self._digest
            previous = self._write_validated(config)
            try:
                if self.started:
                    self._signal_reload()
                else:
                    self._start_existing()
            except Exception:
                self.logs.append("[marzban] reload failed; restoring last working config")
                self._restore(previous)
                self._digest = previous_digest
                if not self.started and previous is not None:
                    self._start_existing()
                raise
            self._digest = digest
            return True

    def reload(self) -> None:
        with self._lock:
            self._validate_file(str(self.config_path))
            self._signal_reload()

    def stop(self) -> None:
        with self._lock:
            if not self.started:
                self.process = None
                return
            process = self.process
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            self.logs.append(f"[marzban] sing-box stopped, pid={process.pid}")
            self.process = None

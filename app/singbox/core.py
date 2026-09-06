from __future__ import annotations

import atexit
import hashlib
import json
import os
import subprocess
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
        self.logs = deque(maxlen=200)
        atexit.register(self.stop)

    @property
    def started(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def version(self) -> str:
        return subprocess.check_output(
            [self.executable_path, "version"], stderr=subprocess.STDOUT, text=True
        ).splitlines()[0]

    def _capture_logs(self):
        while self.process and self.process.stdout:
            line = self.process.stdout.readline()
            if line:
                self.logs.append(line.rstrip())
            elif self.process.poll() is not None:
                break

    def _validate_file(self, path: str) -> None:
        result = subprocess.run(
            [self.executable_path, "check", "-c", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
        )
        if result.returncode:
            raise ValueError(f"Invalid sing-box config: {result.stdout.strip()}")

    def _start_existing(self) -> None:
        if self.started:
            return
        self.process = subprocess.Popen(
            [self.executable_path, "run", "-c", str(self.config_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        threading.Thread(target=self._capture_logs, daemon=True).start()

    def apply(self, config: dict) -> bool:
        payload = json.dumps(config, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with self._lock:
            if digest == self._digest and self.started:
                return False
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(
                prefix=".marzban-sing-box-", suffix=".json.tmp", dir=self.config_path.parent
            )
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
            self.stop()
            self._start_existing()
            self._digest = digest
            return True

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
            self.process = None

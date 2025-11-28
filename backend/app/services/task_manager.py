from __future__ import annotations

import time
import uuid
from enum import Enum
from threading import Thread, Lock
from typing import Any, Dict, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


class TaskManager:
    """简单的内存任务管理器，用于长耗时异常检测任务。

    注意：
    - 仅适用于单进程部署；多进程/多实例需要换成 Redis 等中心存储。
    - 服务重启后任务不会恢复。
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def create_task(self, params: Dict[str, Any]) -> str:
        task_id = f"anomaly_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._tasks[task_id] = {
                "status": TaskStatus.PENDING,
                "progress": 0.0,
                "params": params,
                "result": None,
                "error": None,
                "created_at": time.time(),
            }
        return task_id

    def start_task(self, task_id: str, worker) -> None:
        """在后台线程中启动任务执行。"""

        def _run() -> None:
            self.update(task_id, status=TaskStatus.RUNNING, progress=0.0)
            try:
                params = self.get(task_id).get("params", {}) if self.get(task_id) else {}
                result = worker(task_id, params, self)
                self.update(task_id, status=TaskStatus.FINISHED, progress=1.0, result=result)
            except Exception as e:  # noqa: BLE001
                self.update(task_id, status=TaskStatus.FAILED, error=str(e))

        t = Thread(target=_run, daemon=True)
        t.start()

    def update(self, task_id: str, **fields: Any) -> None:
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].update(fields)

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._tasks.get(task_id)


# 全局任务管理实例
task_manager = TaskManager()

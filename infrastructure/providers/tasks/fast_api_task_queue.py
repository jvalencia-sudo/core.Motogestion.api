import uuid
from typing import Callable, Dict, Any, Optional

from fastapi import BackgroundTasks

from infrastructure.providers.tasks.task_queue_provider import TaskQueueBaseProvider


class FastAPITaskQueue(TaskQueueBaseProvider):
    """Implementation of TaskQueueBase using FastAPI BackgroundTasks."""

    def __init__(self, queue: BackgroundTasks):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.queue = queue

    def _wrapper(self, task_func: Callable, task_id: str, *args, **kwargs):
        """Wrapper to execute the task and store the result."""
        try:
            self.tasks[task_id]["status"] = "IN_PROGRESS"
            result = task_func(*args, **kwargs)
            self.tasks[task_id]["status"] = "COMPLETED"
            self.tasks[task_id]["result"] = result
        except Exception as e:
            self.tasks[task_id]["status"] = "FAILED"
            self.tasks[task_id]["result"] = str(e)

    def enqueue_task(self, task_func: Callable, *args, **kwargs) -> str:
        """Enqueues a function in FastAPI BackgroundTasks."""
        if not callable(task_func):
            raise ValueError("task_func must be a callable function")

        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {"status": "PENDING", "result": None}

        self.queue.add_task(self._wrapper, task_func, task_id, *args, **kwargs)

        return task_id

    def get_task_status(self, task_id: str) -> str:
        """Gets the status of a task."""
        return self.tasks.get(task_id, {}).get("status", "UNKNOWN")

    def get_task_result(self, task_id: str) -> Optional[Any]:
        """Gets the result of a completed task."""
        return self.tasks.get(task_id, {}).get("result")

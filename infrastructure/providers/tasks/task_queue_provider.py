from abc import ABC, abstractmethod
from typing import Any, Optional, Callable


class TaskQueueBaseProvider(ABC):
    """Abstract base class for background task queueing systems."""

    @abstractmethod
    def enqueue_task(self, task_func: Callable, *args, **kwargs) -> str:
        """Adds a task to the queue.

        Returns:
            str: A task ID that can be used to track the task status.
        """
        pass

    @abstractmethod
    def get_task_status(self, task_id: str) -> str:
        """Gets the status of a task.

        Returns:
            str: The task status (e.g., 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED').
        """
        pass

    @abstractmethod
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """Retrieves the result of a completed task.

        Returns:
            Optional[Any]: The result of the task, or None if not completed.
        """
        pass

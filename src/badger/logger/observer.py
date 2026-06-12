"""
observers...
"""

from datetime import datetime

from badger.logger.event import Events, Solution


class Observer:
    def update(self, event: Events, solution: Solution) -> None:
        raise NotImplementedError


class _Tracker(object):
    def __init__(self) -> None:
        self._iterations = 0

        self._start_time: datetime | None = None
        self._previous_time: datetime | None = None

    def _update_tracker(self, event: Events, solution: Solution) -> None:
        if event == Events.OPTIMIZATION_STEP:
            self._iterations += 1

    def _time_metrics(self) -> tuple[str, float, float]:
        now = datetime.now()
        if self._start_time is None:
            self._start_time = now
        if self._previous_time is None:
            self._previous_time = now

        time_elapsed = now - self._start_time
        time_delta = now - self._previous_time

        self._previous_time = now
        return (
            now.strftime("%Y-%m-%d %H:%M:%S"),
            time_elapsed.total_seconds(),
            time_delta.total_seconds(),
        )

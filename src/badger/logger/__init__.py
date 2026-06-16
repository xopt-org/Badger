from __future__ import print_function

import json
import os
from typing import Callable

from badger.logger.event import Events, Solution
from badger.logger.observer import _Tracker
from badger.logger.util import Colours


class ScreenLogger(_Tracker):
    _default_cell_size = 10
    _default_precision = 4

    def __init__(self, verbose: int = 2) -> None:
        self._verbose = verbose
        self._header_length: int | None = None
        super().__init__()

    @property
    def verbose(self) -> int:
        return self._verbose

    @verbose.setter
    def verbose(self, v: int) -> None:
        self._verbose = v

    def _format_number(self, x: int | float) -> str:
        if isinstance(x, int):
            s = "{x:< {s}}".format(
                x=x,
                s=self._default_cell_size,
            )
        else:
            s = "{x:< {s}.{p}}".format(
                x=x,
                s=self._default_cell_size,
                p=self._default_precision,
            )

        if len(s) > self._default_cell_size:
            if "." in s:
                return s[: self._default_cell_size]
            else:
                return s[: self._default_cell_size - 3] + "..."
        return s

    def _format_key(self, key: str) -> str:
        s = "{key:^{s}}".format(key=key, s=self._default_cell_size)
        if len(s) > self._default_cell_size:
            return s[: self._default_cell_size - 3] + "..."
        return s

    def _step(
        self,
        solution: Solution,
        colour: Callable[[str], str] = Colours.black,
    ) -> str:
        # solution: (x: 1d array, y: 1d array, c: 1d array, s: 1d array, is_optimal: bool,
        #            vars: str list, obses: str list, cons: str list, stas: str list)
        cells: list[str] = []

        cells.append(self._format_number(self._iterations + 1))

        for o in solution.objectives or []:
            cells.append(self._format_number(o))

        for c in solution.constraints or []:
            cells.append(self._format_number(c))

        for v in solution.variables or []:
            cells.append(self._format_number(v))

        for s in solution.states or []:
            cells.append(self._format_number(s))  # TODO: deal with the str case

        return "| " + " | ".join(map(colour, cells)) + " |"

    def _header(
        self,
        solution: Solution,
    ) -> str:
        cells = []
        cells.append(self._format_key("iter"))

        for obj in solution.objective_names:
            cells.append(self._format_key(obj))

        for con in solution.constraint_names:
            cells.append(self._format_key(con))

        for var in solution.variable_names:
            cells.append(self._format_key(var))

        for obs in solution.observable_names:
            cells.append(self._format_key(obs))

        line: str = "| " + " | ".join(cells) + " |"
        self._header_length = len(line)
        return line + "\n" + ("-" * self._header_length)

    def _is_new_max(
        self,
        solution: Solution,
    ) -> bool:
        return solution.is_optimal

    def update(
        self,
        event: Events,
        solution: Solution,
    ) -> None:
        if event == Events.OPTIMIZATION_START:
            line = self._header(solution) + "\n"
        elif event == Events.OPTIMIZATION_STEP:
            is_new_max = self._is_new_max(solution)
            if self._verbose == 1 and not is_new_max:
                line = ""
            else:
                colour = Colours.purple if is_new_max else Colours.black
                line = self._step(solution, colour=colour) + "\n"
        elif event == Events.OPTIMIZATION_END:
            line = "=" * (self._header_length or 0) + "\n"

        if self._verbose:
            print(line, end="")
        self._update_tracker(event, solution)


def _get_default_logger(verbose: int) -> ScreenLogger:
    return ScreenLogger(verbose=verbose)


class JSONLogger(_Tracker):
    def __init__(self, path: str, reset: bool = True) -> None:
        self._path = path if path[-5:] == ".json" else path + ".json"
        if reset:
            try:
                os.remove(self._path)
            except OSError:
                pass
        super(JSONLogger, self).__init__()

    def update(self, event: Events, solution: Solution) -> None:
        if event == Events.OPTIMIZATION_STEP:
            data: dict[str, object] = {
                "x": solution.variables,
                "y": solution.objectives,
                "c": solution.constraints,
                "s": solution.states,
                "is_optimal": solution.is_optimal,
            }

            now, time_elapsed, time_delta = self._time_metrics()
            data["datetime"] = {
                "datetime": now,
                "elapsed": time_elapsed,
                "delta": time_delta,
            }

            with open(self._path, "a") as f:
                f.write(json.dumps(data) + "\n")

        self._update_tracker(event, solution)

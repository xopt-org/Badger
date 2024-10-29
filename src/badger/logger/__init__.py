from __future__ import print_function
import os
import json

from badger.logger.observer import _Tracker
from badger.logger.event import Events
from badger.logger.util import Colours


def _get_default_logger(verbose):
    return ScreenLogger(verbose=verbose)


class ScreenLogger(_Tracker):
    _default_cell_size = 10
    _default_precision = 4

    def __init__(self, verbose=2):
        self._verbose = verbose
        self._header_length = None
        super(ScreenLogger, self).__init__()

    @property
    def verbose(self):
        return self._verbose

    @verbose.setter
    def verbose(self, v):
        self._verbose = v

    def _format_number(self, x):
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

    def _format_key(self, key):
        s = "{key:^{s}}".format(key=key, s=self._default_cell_size)
        if len(s) > self._default_cell_size:
            return s[: self._default_cell_size - 3] + "..."
        return s

    def _step(self, solution, colour=Colours.black):
        # solution: (x: 1d array, y: 1d array, c: 1d array, s: 1d array, is_optimal: bool,
        #            vars: str list, obses: str list, cons: str list, stas: str list)
        cells = []

        cells.append(self._format_number(self._iterations + 1))

        for o in solution[1]:
            cells.append(self._format_number(o))

        for c in solution[2]:
            cells.append(self._format_number(c))

        for v in solution[0]:
            cells.append(self._format_number(v))

        for s in solution[3]:
            cells.append(self._format_number(s))  # TODO: deal with the str case

        return "| " + " | ".join(map(colour, cells)) + " |"

    def _header(self, solution):
        cells = []
        cells.append(self._format_key("iter"))

        for obs in solution[6]:
            cells.append(self._format_key(obs))

        for con in solution[7]:
            cells.append(self._format_key(con))

        for var in solution[5]:
            cells.append(self._format_key(var))

        for sta in solution[8]:
            cells.append(self._format_key(sta))

        line = "| " + " | ".join(cells) + " |"
        self._header_length = len(line)
        return line + "\n" + ("-" * self._header_length)

    def _is_new_max(self, solution):
        return solution[4]

    def update(self, event, solution):
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
            line = "=" * self._header_length + "\n"

        if self._verbose:
            print(line, end="")
        self._update_tracker(event, solution)


class JSONLogger(_Tracker):
    def __init__(self, path, reset=True):
        self._path = path if path[-5:] == ".json" else path + ".json"
        if reset:
            try:
                os.remove(self._path)
            except OSError:
                pass
        super(JSONLogger, self).__init__()

    def update(self, event, solution):
        if event == Events.OPTIMIZATION_STEP:
            data = {
                "x": solution[0],
                "y": solution[1],
                "c": solution[2],
                "s": solution[3],
                "is_optimal": solution[4],
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

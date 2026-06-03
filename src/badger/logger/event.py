"""Event constants for the Badger optimization lifecycle. Used to notify
loggers and observers of optimization start, step, and end events."""


class Events:
    OPTIMIZATION_START = "optimization:start"
    OPTIMIZATION_STEP = "optimization:step"
    OPTIMIZATION_END = "optimization:end"


DEFAULT_EVENTS = [
    Events.OPTIMIZATION_START,
    Events.OPTIMIZATION_STEP,
    Events.OPTIMIZATION_END,
]

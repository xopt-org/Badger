"""Event constants (start, step, end) that the optimization loop fires
to notify loggers and observers of progress."""


class Events:
    OPTIMIZATION_START = "optimization:start"
    OPTIMIZATION_STEP = "optimization:step"
    OPTIMIZATION_END = "optimization:end"


DEFAULT_EVENTS = [
    Events.OPTIMIZATION_START,
    Events.OPTIMIZATION_STEP,
    Events.OPTIMIZATION_END,
]

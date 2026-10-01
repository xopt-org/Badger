"""Shared TypedDict contract for the analysis extensions.

``InteractionParameters`` is the base set of fields consumed by
``MatplotlibInteractionHandler``. Every extension's own options TypedDict should
inherit from it so the handler works with any extension, current or future."""

from typing import NotRequired, TypedDict


class InteractionParameters(TypedDict):
    """Fields the shared plot interaction handler reads and writes.

    ``variable_1``/``variable_2`` index into ``variables`` to identify the plotted
    axes. The reference-point fields are only present for extensions that support
    reference points, so they are optional."""

    variable_1: int
    variable_2: int
    variables: list[str]
    reference_points: NotRequired[dict[str, float]]
    reference_points_range: NotRequired[dict[str, tuple[float, float]]]

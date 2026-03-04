---
sidebar_position: 3
---

# Multi-Objective Bayesian Optimization

Multi-Objective Bayesian Optimization (MOBO) aims to determine the best trade-offs between multiple objectives, known as the Pareto Front. Badger implements MOBO using the Expected Hypervolume Improvement (EHVI) acquisition function, which selects points that are more likely to maximally increase the Pareto Front hypervolume. The hypervolume describes the geometric area (scaled to n dimensions equal to n variables) which can be said to be ‘dominated’ by either by ‘filling in’ missing regions of the Pareto Front to increase detail or by selecting observations which are predicted to expand the Pareto Front by dominating current nondominated points. This is an ideal general purpose multi-objective optimizer when objective evaluations cannot be massively parallelized (< 10 parallel evaluations).

## Parameters
- `numerical_optimizer` : Numerical method for finding the maximum value of the aquisition function at each optimization step. Default is LBFGS.
- `max_travel_distances` : Optional list of maximum step sizes, as floats, for each variable. If provided must be the same length as number of variables. Each distance will be applied as an additional constraint on the bounds for each optimization step. For example, if a max_travel_distance of [1.0] is given for a magnet, each step of the optimization will be constrained to a distance of +- 1.0kG from the current value.
- `reference_point` : Dict specifying reference point for multi-objective optimization

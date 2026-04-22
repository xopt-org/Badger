---
sidebar_position: 2
---

# Upper Confidence Bound

[Bayesian Optimization](./../algorithms-overview) algorithms are machine learning-based algorithms that are particularly well suited to efficiently optimizing noisy objectives with few iterations. Upper Confidence Bound is an acquisition function for Bayesian optimization which explicitly specifies a tradeoff between exploration and exploitation by assigning value to new points based on combination of predicted mean and variance with a weighting factor of β. Higher values of β will bias towards exploration, while lower values will bias towards exploitation.

**Advantages:**
- Able to handle constraints during optimization
- Explicit and tunable weighting factor β for biasing towards exploration vs exploitation
- Creates an online surrogate model of the objective and any constraint functions, which can be used during or after optimization
- Can incorporate rich prior information about the optimization problem to improve convergence
- Handles measurement uncertainty and/or noisy objectives

**Disadvantages:**
- β must be set correctly prior to optimization. Performs poorly if the weighting factor β is set incorrectly

## Parameters
- `beta` : Beta parameter for UCB optimization, controlling the trade-off between exploration
    and exploitation. Higher values of beta prioritize exploration. Default value of beta=2 is a good starting point.
- `turbo_controller` : Dynamically constrains the search space to a region around the best point. This can be helpful for preventing Expected Improvement from over-valuing points with high uncertainty at the edges of the scan range.
    - `null` : None
    - `optimizeTurboController` : Trust Region Bayesian Optimization restricts optimization to a region centered around the best previously observed point. This improves convergence and prevents the model from sampling points at the extremes of the parameter space. The trust region is expanded and contracted based on the number of successful (observations that improve over the best observed point) or unsuccessful (no improvement) observations in a row.
    - `safetyTurboController` : 'Safety' based Trust Region Bayesian Optimization can only be used if there is at least one constraint, and centers the trust region on the center-of-mass location of valid points (points that satisfy all constraints). The trust region is expanded and contracted based on the number of successful (observations that satisfy all constraints) or unsuccessful (observations that don't) observations in a row
- `numerical_optimizer` : Numerical method for finding the maximum value of the acquisition function at each optimization step. Default is LBFGS
- `max_travel_distances` : Optional list of maximum step sizes, as floats, for each variable. If provided must be the same length as number of variables. Each distance will be applied as an additional constraint on the bounds for each optimization step. For example, if a max_travel_distance of [1.0] is given for a magnet, each step of the optimization will be constrained to a distance of +- 1.0kG from the current value.

---
sidebar_position: 1
---

# Expected Improvement

[Bayesian Optimization](./../algorithms-overview) algorithms are machine learning-based algorithms that are particularly well suited to efficiently optimizing noisy objectives with few iterations. Expected Improvement (`EI`) is an acquisition function for Bayesian Optimization which determines the value of future points by calculating the expectation value of improvement over the best previously observed point. This emphasizes choosing points that are either predicted to be optimal, have a large variance, or a combination of both, thereby balancing exploration and exploitation.

**Advantages:**
- Able to handle constraints during optimization
- Global or local optimization depending on algorithm specifications
- Creates an online surrogate model of the objective and any constraint functions, which can be used during or after optimization
- Can incorporate rich prior information about the optimization problem to improve convergence
- Explicitly handles measurement uncertainty and/or noisy objectives

**Disadvantages:**
- Numerous hyperparameters can affect performance and increase complexity for users
- Global optimization algorithms like `EI` don’t increase monotonically and can be unfamiliar if users expect to see strong convergence towards optimal values. This can make it difficult to determine when the algorithm has found an optimal point.
- Large uncertainties at the edges can lead `EI` to overprioritize exploration and jump around the ends of the parameter space, especially in high-dimensional problems.

## Parameters
- `turbo_controller` : Dynamically constrains the search space to a region around the best point. This can be helpful for preventing Expected Improvement from over-valuing points with high uncertainty at the edges of the scan range.
    - `null` : None
    - `optimizeTurboController` : Trust Region Bayesian Optimization restricts optimization to a region centered around the best previously observed point. This improves convergence and prevents the model from sampling points at the extremes of the parameter space. The trust region is expanded and contracted based on the number of successful (observations that improve over the best observed point) or unsuccessful (no improvement) observations in a row.
    - `safetyTurboController` : 'Safety' based Trust Region Bayesian Optimization can only be used if there is at least one constraint, and centers the trust region on the center-of-mass location of valid points (points that satisfy all constraints). The trust region is expanded and contracted based on the number of successful (observations that satisfy all constraints) or unsuccessful (observations that don't) observations in a row
- `numerical_optimizer` : Numerical method for finding the maximum value of the acquisition function at each optimization step. Default is LBFGS
- `max_travel_distances` : Optional list of maximum step sizes, as floats, for each variable. If provided must be the same length as number of variables. Each distance will be applied as an additional constraint on the bounds for each optimization step. For example, if a max_travel_distance of [1.0] is given for a magnet, each step of the optimization will be constrained to a distance of +- 1.0kG from the current value.

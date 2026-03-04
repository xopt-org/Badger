---
sidebar_position: 4
---

# Optimization Algorithms Overview

# Bayesian Algorithms

Bayesian Optimization (BO) is an iterative, model-based optimization algorithm that is particularly well suited for sample-efficient optimization of noisy, expensive-to-evaluate objectives. Bayesian Optimization consists of three steps:

1.	*Construct a statistical model of the objective and any constraint functions, based on measured data.* This is generally done using Gaussian Process models, which use Bayes’ rule to predict probability distributions of function values at various locations based on measured data. Values close to observed points will likely be strongly correlated, with uncertainty increasing as the model gets farther from measured data, like a vibrating string with a collection of fixed nodes.

2.	*Define an acquisition function based on the model, which describes the potential value future measurements.* Acquisition functions aim to perform global optimization by balancing *exploration* (Value areas with high uncertainty) and *exploitation* (Value areas predicted to be optimal). The two most commonly used acquisition functions are expected improvement and upper confidence bound. **Expected Improvement** determines the value of future points by calculating an expectation value of improvement over the best previously observed point. This emphasizes choosing points that are either predicted to be optimal, have a large variance, or a combination of both. **Upper Confidence Bound** explicitly specifies a tradeoff between exploration and exploitation by assigning value to new points based on a linear combination of predicted mean and variance with a weighting factor of `β` – higher values of `β` will bias towards exploration, while lower values will bias towards exploitation.

3.	*Find the point which maximizes the acquisition function, i.e., is predicted to provide the most value towards the optimization.* This is in itself an optimization problem and is generally performed using a gradient descent algorithm such as LBFGS, with parallel optimization from multiple random starting points improving the chances of finding a global optimum.

Paraphrased from: *R. Roussel, A.L. Edelen, T. Boltz, D. Kennedy, Z. Zhang, F. Ji, X. Huang, D. Ratner, A.S. Garcia, C. Xu, et al., Bayesian optimization algorithms for accelerator physics, Phys. Rev. Accel. Beams 27 (8) (2024) 084801.*


## Expected Improvement (Bayesian Optimization)

[Expected Improvement](./generators/expected_improvement) is an acquisition function for Bayesian Optimization which determines the value of future points by calculating the expectation value of improvement over the best previously observed point. This emphasizes choosing points that are either predicted to be optimal, have a large variance, or a combination of both, thereby balancing exploration and exploitation.

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

## Upper Confidence Bound

[Upper Confidence Bound](./generators/upper_confidence_bound) is an acquisition function for Bayesian optimization which explicitly specifies a tradeoff between exploration and exploitation by assigning value to new points based on combination of predicted mean and variance with a weighting factor of β. Higher values of β will bias towards exploration, while lower values will bias towards exploitation.

**Advantages:**
- Able to handle constraints during optimization
- Explicit and tunable weighting factor β for biasing towards exploration vs exploitation
- Creates an online surrogate model of the objective and any constraint functions, which can be used during or after optimization
- Can incorporate rich prior information about the optimization problem to improve convergence
- Handles measurement uncertainty and/or noisy objectives

**Disadvantages:**
- β must be set correctly prior to optimization. Performs poorly if the weighting factor β is set incorrectly

# Iterative Algorithms

## Nelder-Mead

[Nelder-Mead](./generators/neldermead) is an iterative downhill simplex algorithm which seeks to find local optima by sampling initial points and then using a heuristic to choose the next point during each iteration. Nelder-Mead has been widely used inside accelerator physics.

**Advantages:**
- Low computational cost
- Historically proven performance in the context of accelerator physics
- Automatic/adaptive hyperparameter specification depending on problem characteristics

**Disadvantages:**
- Local optimizer – sensitive to initial starting conditions
- Sensitive to measurement noise which can negatively impact convergence to optimum
- Scales poorly to higher dimensional problems
- Cannot handle observational constraints

## Extremum Seeking

[Extremum Seeking](./generators/extremum_seeking) performs small oscillations to measurement to slowly move towards minimum. This algorithm uses a sinusoidal sampling strategy for each parameter to slowly drift towards optimal operating conditions and track changes in the optimal operating conditions over time. It’s useful for time dependent optimization, where short term drifts in accelerator conditions can lead to a time dependent objective function.

**Advantages:**
- Low computational cost
- Can track time-dependent drifts of the objective function to maintain an optimal operating configuration

**Disadvantages:**
- Local optimizer, sensitive to initial starting conditions
- Additional hyperparameters that must be tuned to a given optimization problem
- Scales poorly to higher dimensional problems
- Cannot handle observational constraints


## RCDS

[Robust Conjugate Direction Search](./generators/rcds) makes decisions via successive local approximations of the objective function to converge to an optimum. RCDS may be more efficient than Nelder-Mead but requires multiple iterations initially to establish a local model of the objective function before starting to optimize.

**Advantages:**
- Low computational cost
- Historically proven performance in the context of accelerator physics
- Can account for measurement noise via algorithm hyperparameter
- Can control scaling of step size

**Disadvantages:**
- Local optimizer, sensitive to initial starting conditions
- Scales poorly to higher dimensional problems
- Cannot handle observational constraints

# Other

## Random

Generates random points to sample from within the input space

## Latin Hypercube

Similar to random sampling but divides the input space into equal-probability sections along each variable to achieve a more uniform sampling distribution.

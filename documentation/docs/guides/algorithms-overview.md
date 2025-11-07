---
sidebar_position: 4
---

# Optimization Algorithms Overview

## Nelder-Mead

Iterative downhill simplex algorithm which seeks to find local optima by sampling initial points and then using a heuristic to choose the next point during each iteration. Nelder-Mead has been widely used inside accelerator physics.

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

Perform small oscillations to measurement to slowly move towards minimum. This algorithm uses a sinusoidal sampling strategy for each parameter to slowly drift towards optimal operating conditions and track time dependent changes in the optimal operating conditions over time. It’s useful for time dependent optimization, where short term drifts in accelerator conditions can lead to a time dependent objective function.

**Advantages:**
- Low computational cost
- Can track time-dependent drifts of the objective function to maintain an optimal operating configuration

**Disadvantages:**
- Local optimizer, sensitive to initial starting conditions
- Additional hyperparameters that must be tuned to a given optimization problem
- Scales poorly to higher dimensional problems
- Cannot handle observational constraints

## Expected Improvement (Bayesian Optimization)

Bayesian Optimization (BO) algorithms are machine learning-based algorithms that are particularly well suited to efficiently optimizing noisy objectives with few iterations. Using data collected during and/or prior to optimization, BO algorithms use Bayesian statistics to build a model of the objective function that predicts a distribution of possible function values at each point in parameter space. It then uses an acquisition function to make sampling decisions based on determining the global optimum of the objective function.

**Advantages:**
- Global or local optimization depending on algorithm specifications
- Creates an online surrogate model of the objective and any constraint functions, which can be used during or after optimization
- Can account for observational constraints
- Can incorporate rich prior information about the optimization problem to improve convergence
- Explicitly handles measurement uncertainty and/or noisy objectives

**Disadvantages:**
- Potentially significant computational costs, especially after many iterations
- Numerous hyperparameters which can affect performance

## RCDS

Robust Conjugate Direction Search makes decisions via successive local approximations of the objective function to converge to an optimum. RCDS may be more efficient than Nelder-Mead but requires multiple iterations initially to establish a local model of the objective function before starting to optimize.

**Advantages:**
- Low computational cost
- Historically proven performance in the context of accelerator physics
- Can account for measurement noise via algorithm hyperparameter
- Can control scaling of step size

**Disadvantages:**
- Local optimizer, sensitive to initial starting conditions
- Scales poorly to higher dimensional problems
- Cannot handle observational constraints

---
sidebar_position: 6
---

# RCDS

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

## Parameters
- `noise` : Estimated noise level.
- `step` : Step size for the optimization.

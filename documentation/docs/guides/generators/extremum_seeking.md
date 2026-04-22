---
sidebar_position: 5
---

# Extremum Seeking

Perform small oscillations to measurement to slowly move towards minimum. This algorithm uses a sinusoidal sampling strategy for each parameter to slowly drift towards optimal operating conditions and track changes in the optimal operating conditions over time. It’s useful for time dependent optimization, where short term drifts in accelerator conditions can lead to a time dependent objective function.

**Advantages:**
- Low computational cost
- Can track time-dependent drifts of the objective function to maintain an optimal operating configuration

**Disadvantages:**
- Local optimizer, sensitive to initial starting conditions
- Additional hyperparameters that must be tuned to a given optimization problem
- Scales poorly to higher dimensional problems
- Cannot handle observational constraints

## Parameters
- `k` : Feedback gain
- `oscillation_size` : Oscillation size
- `decay_rate` : Decay rate

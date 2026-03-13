---
sidebar_position: 1
---

# Introduction

Badger is a graphical user interface for production-level optimization in accelerator control rooms. 

Built on top of the [Xopt](https://github.com/xopt-org/Xopt) optimization toolkit, Badger makes advanced optimization algorithms accessible to operators and physicists without requiring programming expertise. 

![Badger architecture](/img/intro/Badger-routine.png)


## Optimization Algorithms

Badger provides access to Xopt's comprehensive algorithm library, including:


- **Bayesian Optimization** (Expected Improvement, Upper Confidence Bound) - Sample-efficient global search with constraint handling
- **Nelder-Mead** - Fast local optimization with adaptive parameters
- **Extremum Seeking** - Tracks time-dependent optimal conditions
- **RCDS** - Noise-tolerant local search using successive approximations
- **Sampling methods** - Random and Latin Hypercube for space exploration

These algorithms have been proven effective across diverse accelerator optimization tasks, from beam emittance minimization to FEL pulse intensity maximization. Detailed information about each of the algorithms can be found in  [algorithms overview](guides/algorithms-overview) section.



## Community-Driven Development

Badger is part of a collaborative effort across multiple accelerator facilities to develop standardized optimization tools. The platform is actively used and co-developed by:

![Community](/img/intro/community.png)

### Domestic Facilities:

- SLAC (LCLS, LCLS-II, FACET-II)
- Fermilab (PIP-II, Booster)
- Argonne National Laboratory (ATLAS, APS)
- Brookhaven National Laboratory


### International Facilities:

- European XFEL (Germany)
- ESRF (France)
- And growing...


## From Research to Operations

Badger bridges the gap between cutting-edge optimization research and day-to-day accelerator operations, making advanced ML/AI techniques accessible to control room staff during routine beam tuning, experiment setup, and performance optimization.
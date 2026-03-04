---
sidebar_position: 8
---

# Latin Hypercube

Perform latin hypercube sampling of the evaluation function. Similar to random sampling but divides the input space into equal-probability sections along each variable to achieve a more uniform sampling distribution.


## Parameters
- `batch_size`: Number of samples to generate at a time
- `scramble`: If False, center samples within cells of a multi-dimensional grid. Otherwise, samples are randomly placed within cells of the grid.
- `optimization`: Whether to use an optimization scheme to improve the quality after sampling.
- `strength`: Parameter for strength of sampling, related to dimensions of orthogonality.
- `seed`: Random seed.

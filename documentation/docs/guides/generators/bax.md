---
sidebar_position: 1
---

# BAX

BAX is an information-seeking Bayesian optimization strategy. It is particularly suited for optimizing objective functions that are computed from multiple independent measurements (e.g. an emittance measurement performed by scanning a quadrupole over many focusing strengths and observing the effect on the transverse beam size). When using BAX for such optimization problems, the objective function is never directly evaluated. Instead, the underlying observable quantities that are used to compute the objective function are measured - without the need for these measurements to be performed in any particular pattern - and a "virtual" objective is computed from a GP model of these observables as a function of the input variables. Bayesian samples drawn from the virtual objective model are then optimized with respect to the input variables at every BAX iteration, and the distribution of sample optima are used to estimate the Expected Information Gain. Using the Expected Information Gain as an acquisition function provides an optimal strategy for selecting individual observations that will most efficiently narrow down the distribution of possible solutions.

**Advantages:**

- Able to optimize objective functions with complex (multi-step) measurement processes without ever performing a complete objective function measurement.
- Can more efficiently learn how the input variables affect the objective function by selecting individual measurements that provide maximum information.

**Disadvantages:**

- Because every BAX iteration involves many "virtual" optimization problems in which samples of the virtual objective are numerically optimized before computing the acquisition function, BAX iterations can be slow. Only if the objective function measurement is sufficiently complex and time-consuming will BAX be a preferred strategy (e.g. 1-2 mins for a traditional emittance measurement).
- For any particular objective function, a special "BAX algorithm" class must be written to support the virtual objective modeling and optimization. As such, only a limited number of objectives are supported.

## Parameters

- `numerical_optimizer` : Numerical method for finding the maximum value of the acquisition function at each optimization step. Default is LBFGS
- `algorithm` : BAX algorithm class that defines how to perform virtual objective measurements from the underlying observable GP models.
- `algorithm_results_file` : File location of stored data used for bax visualization extension.

### Algorithm class parameters

- `n_samples` : The number of Bayesian samples of the virtual objective function to optimize during each BAX iteration. Using more samples provides a better estimation of the Expected Information Gain acquisition function, but also increases the computation time.
- `optimizer` : Numerical method for optimizing the virtual objective function samples at each BAX iteration. Currently only supports a genetic algorithm called Differential Evolution.
- Other algorithm parameters are unique to the particular optimization problem for which each BAX algorithm class is designed. For more information on specific BAX algorithm classes, see https://github.com/xopt-org/bax_algorithms

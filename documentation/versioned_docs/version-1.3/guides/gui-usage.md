---
sidebar_position: 1
---

# GUI Usage

## GUI Layout

The Badger GUI is an interface made for optimizing accelerator performance. Behind the scenes, Badger uses Xopt, a python package designed to support a wide variety of control system optimization problems and algorithms. There are four important sections to defining an optimization problem using the Badger GUI: **Environment**, **VOCS**, **Algorithm**, and **Metadata**. The Badger GUI organizes these into three tabs, with Environment + VOCS being combined into a single main tab.

### Environment + VOCS

The **Environment** defines available variables and observables for a specific machine or control system. At SLAC, possible environments include `LCLS`, `FACET`, and `LCLS_II`. Each environment contains information about the variables available within that system, such as their bounds, along with operational parameters for data collection such as number of points, trim delay, fault timeout, and other information related to the interaction between the optimizer and the physical or simulated environment.

Within an environment, an optimization problem can be defined by selecting which variables to adjust, objectives to optimize, and any constraints to follow. **VOCS** represents the subset of variables, objectives, and constraints to be optimized within the environment. You can also add observables within the VOCS section, which the GUI will monitor and display but won’t otherwise interact with. The “Constraints” and “Observables” sections are optional for defining an optimization and are collapsed by default. They can be accessed by clicking on **More** at the bottom of the Environment + VOCS tab.

### Algorithm

The **Algorithm** section lets you select an algorithm to use for optimization. See “*Overview of Different Optimization Algorithms*” for a more detailed overview of different options. Common algorithms used at SLAC are expected improvement and nelder-mead.

### Metadata

**Metadata** includes a name and description for the optimization routine.

### Loading a template

If there is already a template for the optimization you’d like to run, click the **Load Template** button at the upper left of the **Environment + VOCS** tab, and select the appropriate template. Make sure to check the environment parameters, variables and variable ranges, objectives, constraints/observables, and selected algorithm before running the optimization.

---

## To Define a New Optimization Routine

1. **Start by selecting the target environment** from the **Environment** dropdown. Click the **Parameters** button to expand the available environment parameters.

2. **From the “Variables” table select devices to be optimized.**
   The variables table shows all the variables which have been included in the selected environment. You can also toggle the **Show Checked Only** checkbox to only display selected variables. If a device you’d like to try to optimize is not listed, you can scroll to the bottom of the table and enter a new PV. The **Min** and **Max** columns in the table show the bounds of the search space for optimization. If the **Automatic** checkbox above the table is checked, these bounds will be ± some percentage from the current value. Clicking **Set Variable Range** will open a dialog window showing that ratio, and an option to select either relative to current or relative to the full variable range. Unchecking **Automatic** allows you to manually set variable ranges by editing the values in the **Min** and **Max** columns.

3. **If the “Automatic” checkbox is checked, selecting a variable will automatically add a set of initial points.**
   By default, these will be the current value followed by three random points within a fraction of the variable bounds centered around the current value. If **Automatic** is not checked, or to adjust the initial points, you can use the **Add Current** and **Add Random** buttons to configure your own initial points.

4. **Select an objective from the “Objectives” table.**
   Make sure to select whether the objective should be maximized or minimized! Currently only single objective optimization is available, but multi-objective optimization will be supported in the future.

5. **Add constraints and observables.**
   Beneath the **Objectives** table is a collapsable **More** section, which allows you to add Constraints and Observables. The constraints and observables available for selection are based on the selected environment.

6. **Choose an optimization algorithm.**
   There are several different optimization algorithms available within the Badger GUI. Generally, **expected improvement** and **Nelder-Mead** are good choices for online accelerator optimization. To select an algorithm navigate to the "Algorithm" tab. To read more about different algorithms, see the "[Overview of Different Optimization Algorithms](#overview-of-different-optimization-algorithms)” section below.

7. **Metadata:**
   Provide a name and description for your optimization routine.

---

## Running the Optimization

Once the environment, variables, objectives, and algorithm (and any optional constraints and observables) have been defined, the optimization can be started by pressing the green **run** button at the lower center of the GUI. Badger will begin by measuring the objective at the initial points specified in the **Initial Points** table, and will then begin to optimize the selected variables using the chosen algorithm. When the scan is active, the green **run** button will turn into a red **stop** button.

- Once the scan has started, it can be paused/resumed using the **play/pause** button to the left of the **run** button.
- To end the optimization run, press the red **stop** button.

After ending the optimization, you may want to take some sort of action on the variables/devices being optimized. Depending on the algorithm selected, the last point/state sampled may not be the best that was found during the optimization run. To select the best configuration of variables that was measured, press **Jump to Optimal** (star icon button) to the right of the stop/start button. Alternatively, clicking any point in the optimization plot will highlight the variable values at that point in the scan. Once you’ve chosen the solution you’d like to implement, press **Dial in solution** to set devices to the selected values.

To reset all the variables to their values at the beginning of the scan, press the **Reset Environment** button.

While the optimization is running, the values of the variables, objectives, and (if selected) constraints and observables will be plotted in the plot section in the top right corner of the GUI. By default, the X-Axis displays the number of optimization iterations, and the Y-Axis for the variables plot is relative to each variable’s starting value. These options can be changed from the GUI via options in the top right corner, above the plots.

---

## Defining Template Files

To save the current scan parameters as a template from the GUI, navigate to the **Metadata** tab. Click **Save as Template**, and enter an appropriate filename ending in “.yaml”. This will save the Environment, VOCS, Algorithm, and Metadata currently displayed on the GUI to a YAML file, including environment and algorithm parameters and relative variable ranges, and the configuration of initial points.

Templates can also be directly saved or edited as YAML files, with the following format:

```yaml
name: ''            # name of template
description: ''     # description of template
environment:
  name: ''          # environment name
  params: {}        # environment parameters, depend on environment
generator:
  name:             # generator name
  # params will depend on generator
vocs:               # XOPT VOCS
  constants: {}     # {constant_name: value}
  constraints: {}   # {constraint_name: [GREATER_THAN or LESS_THAN, value]}
  objectives: {}    # {objective_name: MINIMIZE or MAXIMIZE}
  observables: []   # list of observable names
  variables: {}     # {variable_name: [lower_bound, upper_bound]}

                    # Note that the variable upper and lower bound should be
                    # the absolute variable range limits, not the limit of the
                    # optimization. The range of the optimization is set based
                    # on vrange_limit_options for each variable, either as a
                    # fraction of the full range or ± a fraction of the
                    # current value.

vrange_limit_options: {}

                    # for each variable:
                    #   variable: {limit_option_idx: 0 or 1, ratio_curr: 0.1, ratio_full: 0.1}
                    # For example:
                    #   QUAD:LTUH:620:BCTRL:
                    #   limit_option_idx: 0
                    #   ratio_curr: 0.1
                    #   ratio_full: 0.1
                    # Note that ratio_curr is the ratio with respect to the current value
                    # and ratio_full is the ratio with respect to the full variable range.
                    # limit_option_idx 0 will use ratio_curr, 1 is ratio_full

relative_to_current: true  # true or false.
initial_point_actions: [{}]  # list of dictionaries

                    # Will be read sequentially.
                    # For example, the two most common options would look like:
                    #
                    # - type: add_curr     # will add the current value of selected vars
                    # - config:
                    #     fraction: 0.1
                    #     method: 0
                    #     n_points: 3
                    #   type: add_rand
                    #
                    # will add three random points for each variable, selected
                    # from within 0.1*(the vrange limit ratio for that
                    # variable) around the current value – i.e. sample n random
                    # points from within a subset of the scan range

critical_constraint_names: []  # list of constraints (from VOCS) to be marked as ‘critical’
badger_version:     # optional but helpful
xopt_version:       # optional but helpful
```
## Overview of Different Optimization Algorithms

### Nelder-Mead

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

### Extremum Seeking

Perform small oscillations to measurement to slowly move towards minimum. This algorithm uses a sinusoidal sampling strategy for each parameter to slowly drift towards optimal operating conditions and track time dependent changes in the optimal operating conditions over time. It’s useful for time dependent optimization, where short term drifts in accelerator conditions can lead to a time dependent objective function.

**Advantages:**
- Low computational cost
- Can track time-dependent drifts of the objective function to maintain an optimal operating configuration

**Disadvantages:**
- Local optimizer, sensitive to initial starting conditions
- Additional hyperparameters that must be tuned to a given optimization problem
- Scales poorly to higher dimensional problems
- Cannot handle observational constraints

### Expected Improvement (Bayesian Optimization)

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

### RCDS

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

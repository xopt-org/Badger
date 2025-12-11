---
sidebar_position: 3
---

# Templates

## Loading a Template

If there is already a template for the optimization you’d like to run, click the **Load Template** button at the upper left of the **Environment + VOCS** tab, and select the appropriate template. Make sure to check the environment parameters, variables and variable ranges, objectives, constraints/observables, and selected algorithm before running the optimization.

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

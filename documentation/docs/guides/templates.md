---
sidebar_position: 3
---

# Templates

## Loading a Template

If there is already a template for the optimization you’d like to run, click the **Load Template** button at the upper left of the **Environment + VOCS** tab, and select the appropriate template. Make sure to check the environment parameters, variables and variable ranges, objectives, constraints/observables, and selected algorithm before running the optimization.

### Note
Users might run into VariableRangeError notification if the limits of the process variables (PVs) in the template differ from the limits of the PVs in the Badger environment.


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
  constants: {}     # {constant_name: value} # optional
  constraints: {}   # {constraint_name: [GREATER_THAN or LESS_THAN, value]} # optional
  objectives: {}    # {objective_name: MINIMIZE or MAXIMIZE}
  observables: []   # list of observable names # optional
  variables: {}     # {variable_name: [lower_bound, upper_bound]}

                    # Important note about variable bounds: the bounds set here will be used
                    # if relative_to_current is set to false. If relative_to_current is true,
                    # these bounds will not be used and the bounds for each variable will be
                    # determined based on the vrange_limit_options below.

vrange_limit_options: {}

                    # for each variable:
                    #   variable: {limit_option_idx: 0 or 1 or 2 or 3, ratio_curr: ratio (float), ratio_full: ratio (float), delta: abs value (float), exact_bounds: [lower, upper] (list[float, float])}
                    #
                    # For example:
                    #   QUAD:LTUH:620:BCTRL:
                    #     limit_option_idx: 2
                    #     ratio_curr: 0.1
                    #     ratio_full: 0.1
                    #     delta: 1.2
                    #     exact_bounds: [45.0, 57.0]
                    # Will set the variable range for QUAD:LTUH:620:BCTRL to a delta (option 2) of +- 1.2 from the current value of the variable.
                    #
                    # Note that ratio_curr is the ratio with respect to the current value,
                    # ratio_full is the ratio with respect to the full variable range, and
                    # delta is an absolute delta around the current value.
                    # limit_option_idx sets the desired option: 0 will use ratio_curr,
                    # 1 is ratio_full, 2 is delta, 3 will use exact_bounds
                    #
                    # The first three methods will calculate bounds around the current variable value when the template
                    # is loaded based on the selected option. If limit_option_idx == 3 for exact_bounds,
                    # the specified bounds will be used regardless of the current value of the variable. If the
                    # exact_bounds option is selected without specifying numerical bounds in vrange_limit_options,
                    # the GUI will use the hard bounds defined above in vocs/variables as a fallback.

relative_to_current: true  # (bool) true or false. If true, variable ranges will be set
                    # for each variable based on vrange_limit_options. If False, variable
                    # ranges will be set to the specified upper and lower bounds from the
                    # variables dictionary in vocs.
initial_point_actions: [{}]  # list of dictionaries
                    # Will be read sequentially.
                    # For example, a common option would look like:
                    #
                    # - type: add_curr
                    #         # will add the current value of selected vars
                    #         # as the first initial point
                    # - config:
                    #     fraction: 0.1
                    #     method: 0
                    #     n_points: 3
                    #   type: add_rand
                    #
                    #   will add three random points (type: add_rand) for each variable, selected
                    #   from within 0.1*[the vrange limit ratio for that
                    #   variable] around the current value - i.e. sample n random
                    #   points from within a subset of the scan range

critical_constraint_names: []  # list of constraints (from VOCS) to be marked as ‘critical’
additional_variables: [] # list of additional variables # optional
formulas: {}        # optional
constraint_formulas: {} # optional
observable_formulas: {} # optional
vrange_hard_limit: {} # optional
badger_version:     # badger version
xopt_version:       # xopt version
```

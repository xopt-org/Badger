---
sidebar_position: 2
---

# Create Environments and Interfaces

Plugins have two types:

- Environment: class
- Interface: class

Interface is the low-level layer between the machine/simulation and the environment that deals with the fundamental communications. It can be treated as an abstract of the underlying control system. Interface is optional **BUT** recommended! The pros of having an interface:

- It can be reused across different environments, so that you don't have to rewrite the same communication logic again and again[^intf-exp]
- Unlike the environment, all the raw data that go through the interface can be recorded and archived, those raw data could include the intermediate measurements/observations that used to calculate the objectives/constraints/states[^env-cons]

Environment, on the other hand, abstracts the specific machine to be optimized. It contains the necessary information regarding the tuning knobs and the measurements, as well as the way to get and/or set them. Environment is the core of defining the optimization problem in Badger and it is mandatory.

This guide will go through the basic components that compose a custom interface/environment by creating a simplest but full-featured interface/environment plugin. Let's get started.

## Create an interface plugin

The file structure of a Badger interface plugin looks like this:

```shell title="Badger interface plugin file structure"
|--<INTERFACE_ID>
    |--__init__.py
    |--configs.yaml
    |--README.md
    |--...
```

Let's create a simple interface that has 9 channels (8 input channels and 1 output channel), where the output channel is the L2 norm of all the input channel values. We'll name it `myintf`.

Assume that the Badger plugin root has been pointed to some directory `PLUGIN_ROOT` on your computer, then we can create a new folder `myintf` inside `PLUGIN_ROOT/interfaces/`, and we put the following files with the given content into the newly created folder:

First the main script file:

```python title="myintf/__init__.py"
from badger import interface


class Interface(interface.Interface):

    name = 'myintf'

    def get_values(self, channel_names: list):
        pass

    def set_values(self, channel_inputs: dict):
        pass
```

Then the configs file:

```yaml title="myintf/configs.yaml"
---
name: myintf
version: "0.1"
dependencies:
  - badger-opt
```

## Create an environment plugin

To let Badger deal with your own optimization problem, you'll need to turn the problem into a custom environment plugin first. An environment in Badger defines how Badger could interact with the "control system" upon which the optimization problem forms up. To be more specific, Badger wants to know:

- What variables can be tuned
- What are the ranges for the tunable variables
- What observations are available (objectives, constraints, anything you would like to monitor in the optimization)

Plus (actually more importantly):

- How to tune one variable
- How to get one observation

And you incorporate those knowledge into Badger by inheriting the `Environment` base class provided by the Badger core, and implementing the corresponding methods.

Let's get a better idea about it by creating a simple custom environment plugin for Badger from the ground up.

### The basics

First off, let's create a file structure like the following:

```shell title="Simplest environment plugin file structure"
|--myenv
    |--__init__.py
    |--configs.yaml
```

Here we'll name our simple custom env as `myenv`, as the folder name shows.

Then put the boilerplate code below into `__init__.py`:

```python title="myenv/__init__.py"
from badger import environment
from badger.interface import Interface


class Environment(environment.Environment):

    name = 'myenv'
    variables = {}
    observables = []

    def get_variables(self, variable_names: list[str]) -> dict:
        return {}

    def set_variables(self, variable_inputs: dict[str, float]):
        pass

    def get_observables(self, observable_names: list[str]) -> dict:
        return {}
```

Several things to note regarding the boilerplate code:

- It should have a class variable called `name`, and it should match the folder name of the plugin
- In order to create a proper Badger env, there are 2 **CLASS** variables:
    - `variables`: A dictionary of all the supported variables, key is the variable name, value is the range of the variable
    - `observables`: A list of all the supported observables

    and 3 methods:
    - `get_variables`: Get a dictionary contains values of a given list of variables
    - `set_variables`: Set the variables in the env with a given dictionary of variables and the target values
    - `get_observables`: Get a dictionary contains values of a given list of observables

    that are required to be implemented.

:::tip

Try to avoid doing time-consuming thing in `__init__` method. Badger would create an instance of the environment when users try to get the details of the plugin (say, when `badger env myenv` is called in CLI mode), so just put some light-computing code there in the constructor would provide the users a smoother experience.

:::

Okay, now we can start to implement the methods. Assume that our sample environment has 3 variables: `x`, `y`, and `z`, with range of [0, 1]. It also has 2 observations: `norm`, and `mean`. Then the `variables` and `observables` class variables should look like:

```python
    variables = {
        'x': [0, 1],
        'y': [0, 1],
        'z': [0, 1],
    }
    observables = ['norm', 'mean']
```

Our custom env is so simple that we don't really need an interface here. Let's implement the getter and setter for the variables:

```python
    # Internal variables start with a single underscore
    _variables = {
        'x': 0,
        'y': 0,
        'z': 0,
    }

    def get_variables(self, variable_names: list[str]) -> dict:
        variable_outputs = {v: self._variables[v] for v in variable_names}

        return variable_outputs

    def set_variables(self, variable_inputs: dict[str, float]):
        for var, x in variable_inputs.items():
            self._variables[var] = x
```

Here we use a dictionary called `_variables` to hold the values for the variables.

Now let's add observable related logic:

```python
    def get_observables(self, observable_names: list[str]) -> dict:
        x = self._variables['x']
        y = self._variables['y']
        z = self._variables['z']

        observable_outputs = {}
        for obs in observable_names:
            if obs == 'norm':
                observable_outputs[obs] = (x ** 2 + y ** 2 + z ** 2) ** 0.5
            elif obs == 'mean':
                observable_outputs[obs] = (x + y + z) / 3

        return observable_outputs
```

At this point, the content of `__init__.py` should be:

```python title="myenv/__init__.py"
import numpy as np
from badger import environment


class Environment(environment.Environment):

    name = 'myenv'

    variables = {
        'x': [0, 1],
        'y': [0, 1],
        'z': [0, 1],
    }
    observables = ['norm', 'mean']

    # Internal variables start with a single underscore
    _variables = {
        'x': 0,
        'y': 0,
        'z': 0,
    }

    def get_variables(self, variable_names: list[str]) -> dict:
        variable_outputs = {v: self._variables[v] for v in variable_names}

        return variable_outputs

    def set_variables(self, variable_inputs: dict[str, float]):
        for var, x in variable_inputs.items():
            self._variables[var] = x

    def get_observables(self, observable_names: list[str]) -> dict:
        x = self._variables['x']
        y = self._variables['y']
        z = self._variables['z']

        observable_outputs = {}
        for obs in observable_names:
            if obs == 'norm':
                observable_outputs[obs] = (x ** 2 + y ** 2 + z ** 2) ** 0.5
            elif obs == 'mean':
                observable_outputs[obs] = (x + y + z) / 3

        return observable_outputs
```

Alright! Our little env is almost done -- even though it doesn’t do much, it already has everything that we need for a Badger environment! To make the plugin complete, we should also incorporate some meta data (such as version number) of our env into `configs.yaml`:

```python title="myenv/configs.yaml"
---
name: myenv
version: "0.1"
dependencies:
  - badger-opt
```

Congrats! Our custom env plugin is ready to go! Let's put the whole folder under `BADGER_PLUGIN_ROOT/environments`, then executing the following command in a terminal (in which the Badger package is available, of course):

```shell
badger env myenv
```

The printouts should look like below. Yay!

```yaml
name: myenv
version: '0.1'
dependencies:
  - badger-opt
params: {}
variables:
  - x: 0 -> 1
  - y: 0 -> 1
  - z: 0 -> 1
observations:
  - norm
  - mean
```

:::caution

Please be sure to use Badger v1.0+

:::

Now you can take `myenv` for a spin -- just write some routine configs and run some algorithm (say, `silly` the random sampler) on our newly created env, to see if everything works as expected.

### Advanced topics

#### Specify variable range

#### Incorperate hyper-parameters

#### Check variable readout

#### Delayed observation

<!-- ```python
from badger import environment
from badger.interface import Interface


class Environment(environment.Environment):

    name = 'myenv'

    def __init__(self, interface: Interface, params):
        super().__init__(interface, params)
        # Add other logic, try to not do time-consuming stuff here

    @staticmethod
    def list_vars():
        return [
            'v1',
            'v2',
            'v3',
        ]

    @staticmethod
    def list_obses():
        return [
            'o1',
            'o2',
        ]

    @staticmethod
    def get_default_params():
        return {
            'delay': 3,
        }

    def _get_vrange(self, var):
        vrange = [-10, 10]

        return vrange

    def _get_var(self, var):
        return self.interface.get_value(var)

    def _set_var(self, var, x):
        self.interface.set_value(var, x)

    def _check_var(self, var):
        return 0

    def vars_changed(self, vars, values):
        time.sleep(self.params['delay'])

    def _get_obs(self, obs):
        return 0
``` -->

## Caveats

### EPICS-related interface/environment

When setting up an interface that uses EPICS. There is a need to run `epics.ca.clear_cache()`[^epics-docs] when both getting and setting values from PVs. This ensures that the new processes do not share connections with previous runs of Badger.

Below is an example that where you should make the `epics.ca.clear_cache()` call in an interface. The same applies for `set_values()` -- you should put `epics.ca.clear_cache()` at the beginning of the function body.

```python {2,6}
def get_values(self, channel_names):
    epics.ca.clear_cache()

    channel_outputs = {}

    values = epics.caget_many(channel_names, timeout=3)
    for i, channel in enumerate(channel_names):
        channel_outputs[channel] = values[i]

    return channel_outputs
```

Also to note, when you uses `PV.get()` to fetch data, the connections must be disconnected by the interface when they are no longer needed. If they are not properly disconnected they will persist between runs and cause a fault in Badger. Here is the example code for the same epics interface but with the `PV` approach.

```python {2,6,7}
def get_values(self, channel_names):
    epics.ca.clear_cache()

    channel_outputs = {}

    pvs = [epics.PV(name) for name in channel_names]
    values = [p.get(timeout=3) for p in pvs]
    for i, channel in enumerate(channel_names):
        channel_outputs[channel] = values[i]

    return channel_outputs
```

[^intf-exp]: One example is that both LCLS and NSLS use Epics as the control system, so an Epics interface can be shared between the LCLS and NSLS Badger environments
[^env-cons]: Environment can only record the VOCS, not the intermediate measurements. Say, to calculate the FEL pulse energy, one needs to average over a buffer of values. It is the averaged value being recorded in the archived run data, not the raw buffers
[^epics-docs]: See https://pyepics.github.io/pyepics/ca.html for notes on the `clear_cache` method

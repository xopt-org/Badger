---
sidebar_position: 4
---

# Create a plugin

Plugins have three types:

- Algorithm: function
- Interface: class
- Environment: class

## Create an algorithm plugin

## Create an interface plugin

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

    def __init__(self, interface: Interface, params):
        super().__init__(interface, params)
        # Add other logic, try to not do time-consuming stuff here

    @staticmethod
    def list_vars():
        return []

    @staticmethod
    def list_obses():
        return []

    def _get_var(self, var):
        return 0

    def _set_var(self, var, x):
        pass

    def _get_obs(self, obs):
        return 0
```

Several things to note regarding the boilerplate code:

- It should have a class variable called `name`, and it should match the folder name of the plugin
- There are 5 methods that are required to be implemented to create a proper Badger env:
    - `list_vars`: Get a list of all the supported variables
    - `list_obses`: Get a list of all the supported observations
    - `_get_var`: Get the value of a specific variable
    - `_set_var`: Set a specific variable to some value
    - `_get_obs`: Get the value of a specific observation

:::tip

As the comment says, try to avoid doing time-consuming thing in `__init__` method. Badger would create an instance of the environment when users try to get the details of the plugin (say, when `badger env myenv` is called in CLI mode), so just put some light-computing code there in the constructor would provide the users a smoother experience.

:::

Okay, now we can start to implement the methods. Assume that our sample environment has 3 variables: `x`, `y`, and `z`, it also has 2 observations: `norm`, and `mean`. Then the `list_vars` and `list_obses` methods should look like:

```python
    @staticmethod
    def list_vars():
        return ['x', 'y', 'z']

    @staticmethod
    def list_obses():
        return ['norm', 'mean']
```

Our custom env is so simple that we don't really need an interface here. Let's implement the getter and setter for the variables:

```python
    def __init__(self, interface: Interface, params):
        super().__init__(interface, params)
        self.variables = {
            'x': 0,
            'y': 0,
            'z': 0,
        }

    def _get_var(self, var):
        return self.variables[var]

    def _set_var(self, var, x):
        self.variables[var] = x
```

Here we use a dictionary called `variables` to hold the values for the variables.

Now let's add observation related logic:

```python
    def _get_obs(self, obs):
        x = self.variables['x']
        y = self.variables['y']
        z = self.variables['z']

        if obs == 'norm':
            return (x ** 2 + y ** 2 + z ** 2) ** 0.5
        elif obs == 'mean':
            return (x + y + z) / 3
```

At this point, the content of `__init__.py` should be:

```python title="myenv/__init__.py"
from badger import environment
from badger.interface import Interface


class Environment(environment.Environment):

    name = 'myenv'

    def __init__(self, interface: Interface, params):
        super().__init__(interface, params)
        self.variables = {
            'x': 0,
            'y': 0,
            'z': 0,
        }

    @staticmethod
    def list_vars():
        return ['x', 'y', 'z']

    @staticmethod
    def list_obses():
        return ['norm', 'mean']

    def _get_var(self, var):
        return self.variables[var]

    def _set_var(self, var, x):
        self.variables[var] = x

    def _get_obs(self, obs):
        x = self.variables['x']
        y = self.variables['y']
        z = self.variables['z']

        if obs == 'norm':
            return (x ** 2 + y ** 2 + z ** 2) ** 0.5
        elif obs == 'mean':
            return (x + y + z) / 3
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
params: null
variables:
  - x: 0 -> 1
  - y: 0 -> 1
  - z: 0 -> 1
observations:
  - norm
  - mean
```

:::caution

If you use an older version of Badger, you would encounter the following error when you do `badger env myenv`:

```
Can't instantiate abstract class Environment with abstract method get_default_params
```

To get around this issue, simply put the following method inside the `myenv` environment class definition:

```python
    @staticmethod
    def get_default_params():
        return None
```

Then you should get the expected printouts. The usage of the `get_default_params` method will be covered in [future sections](#incorperate-hyper-parameters).

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

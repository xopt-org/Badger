---
sidebar_position: 3
---

# API Usage

Badger can be imported as a regular python package, and you could use the plugins/utils that Badger offers in your own python script.

:::note Heads-up

Make sure you have Badger [installed and setup](../getting-started/installation).

:::

## Use an algorithm

Badger has a `get_algo` API to get a specific algorithm.

The following code gets an algorithm named `silly` (which is a random search algorithm) from Badger.

```python
import numpy as np
from badger.factory import get_algo

# Define a test evaluate function
def evaluate(X):
    Y = np.linalg.norm(X, axis=1).reshape(-1, 1)  # objectives
    I = None  # inequality constraints
    E = None  # equality constraints

    # Show the progress
    print(Y)

    return Y, I, E

# Get the silly algorithm from Badger
optimize, configs = get_algo('silly')

# Optimize the test evaluate function
optimize(evaluate, configs['params'])
```

## Use an interface

Badger has a `get_intf` API to get a specific interface.

The following code gets an interface named `silly` and constructs an instance of the interface.

```python
from badger.factory import get_intf

# Get the silly interface from Badger
Interface, configs = get_intf('silly')
intf = Interface(configs['params'])

# Test get/set channels
intf.get_value('c1')
# Output: 0

intf.set_value('c1', 1.0)
intf.get_value('c1')
# Output: 1.0
```

## Use an environment

Badger has a `get_env` API to get a specific environment.

The following code gets and instantiates an environment named `silly` from Badger. Note that it uses the `silly` interface instance `intf` from the [last](#use-an-interface) section.

```python
from badger.factory import get_env

# Get the silly environment from Badger
Environment, configs = get_env('silly')
env = Environment(intf, configs['params'])

# Investigate the silly env
env.list_vars()
# Output: ['q1', 'q2', 'q3', 'q4']

env.list_obses()
# Output: ['l1', 'l2']

env.get_var('q1')  # q1 in env maps to c1 in intf
# Output: 1.0

env.get_obs('l2')  # l2 norm of (q1, q2, q3, q4)
# Output: 1.0

env.set_var('q2', 1)
env.get_obs('l2')
# Output: 1.4142135623730951
```

Now we can define an evaluate function based on the `silly` env, and use the `silly` algorithm from the [use an algorithm](#use-an-algorithm) section to optimize it.

```python
# Define an evaluate function based on the env
def evaluate(X):
    # Note that X is a 2D array
    Y = []
    for x in X:
        env.set_vars(['q1', 'q2', 'q3', 'q4'][:len(x)], x)
        y = env.get_obs('l2')
        Y.append(y)
    Y = np.array(Y).reshape(-1, 1)
    I = None
    E = None

    # Show the progress
    print(Y)

    return Y, I, E

# Optimize the evaluate function with silly algorithm
optimize(evaluate, {'dimension': 4, 'max_iter': 42})
```

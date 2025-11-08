---
sidebar_position: 2
---

# Tutorial (CLI mode)

:::note Heads-up

Make sure you have Badger [installed and setup](./installation).

:::

Let's discover **Badger in less than 5 minutes**. All of the following commands are assumed to be run in a terminal (Mac, Windows, and Linux are supported).

First let's verify that Badger has been installed and configured correctly:

```shell
badger
```

Which should give you something like:

```shell title="output"
name: Badger the optimizer
version: 0.5.3
plugin root: /root/badger/plugins
database root: /root/badger/db
logbook root: /root/badger/logbook
archive root: /root/badger/archived
extensions:
  - xopt
```

## Run and save an optimization

Create a yaml file under your `pwd` (where you would run an optimization with Badger) with the following content:

```yaml title="config.yaml"
variables:
  - x2
objectives:
  - c1
```

To run and save an optimization, run:

```shell
badger run -a silly -e TNK -c config.yaml -s helloworld
```

Badger will ask you to review the optimization routine:

```shell title="output"
Please review the routine to be run:

=== Optimization Routine ===
name: mottled-sloth
algo: silly
env: TNK
algo_params:
  dimension: 1
  max_iter: 42
env_params: null
config:
  variables:
    - x2: 0 -> 3.14159
  objectives:
    - c1: MINIMIZE
  constraints: null

Proceed ([y]/n)?
```

Hit return to confirm. Badger will print out a table of all the evaluated
solutions along the run:

```shell {3,19} title="output"
|    iter    |     c1     |     x2     |
----------------------------------------
|  1         | -1.094     |  0.07432   |
|  2         |  3.563     |  2.159     |
|  3         |  8.749     |  3.138     |
|  4         |  5.351     |  2.54      |
|  5         |  8.17      |  3.045     |
|  6         |  6.536     |  2.763     |
|  7         |  3.007     |  2.027     |
|  8         | -1.089     |  0.1063    |
|  9         |  4.127     |  2.286     |
|  10        |  3.519     |  2.149     |
|  11        |  6.647     |  2.783     |
|  12        |  1.074     |  1.474     |
|  13        | -0.8621    |  0.4878    |
|  14        |  3.821     |  2.218     |
|  15        | -0.9228    |  0.421     |
|  16        |  6.205     |  2.703     |
|  17        | -1.1       |  0.005409  |
|  18        |  8.224     |  3.054     |
|  19        |  7.584     |  2.947     |
|  20        | -0.8961    |  0.4515    |
|  21        | -1.093     |  0.08082   |
|  22        |  1.293     |  1.547     |
|  23        |  2.593     |  1.922     |
|  24        |  5.563     |  2.581     |
|  25        |  2.046     |  1.774     |
|  26        |  2.501     |  1.898     |
|  27        | -0.8853    |  0.4633    |
|  28        | -0.5459    |  0.7444    |
|  29        | -0.8881    |  0.4604    |
|  30        | -0.4806    |  0.787     |
|  31        | -1.1       |  0.01909   |
|  32        |  0.4855    |  1.259     |
|  33        |  0.8217    |  1.386     |
|  34        |  6.036     |  2.671     |
|  35        | -0.7649    |  0.5789    |
|  36        |  0.06972   |  1.082     |
|  37        |  7.325     |  2.903     |
|  38        | -0.7764    |  0.5689    |
|  39        |  6.042     |  2.673     |
|  40        |  5.008     |  2.471     |
|  41        |  4.274     |  2.318     |
|  42        | -0.8561    |  0.4939    |
========================================
```

You would notice that the optimal solutions (in this case
optimal means minimal `c1`) at the evaluation time are highlighted.

In the example above, we use the **silly** algorithm (which is just a random search algorithm) to optimize the **TNK**
environment, as shown in the reviewed routine. Environment **TNK** has 2
variables and 5 observations:

```yaml {7,8,10-14} title="TNK environment"
name: TNK
version: '0.1'
dependencies:
  - numpy
params: null
variables:
  - x1: 0 -> 3.14159
  - x2: 0 -> 3.14159
observations:
  - y1
  - y2
  - c1
  - c2
  - some_array
```

We specify in the `config.yaml` that we would like to tune varaible `x2`, and minimize observation `c1` of environment **TNK** as objective. The configuration that could reproduce the whole optimization setup is called a **routine** in Badger. A routine contains the information of the algorithm, the environment, and the config of the optimization (the variables, the objectives, and the constraints).

We just saved the routine of the run as `helloworld`. Now you could view the routine again by:

```shell
badger routine helloworld
```

## Rerun an optimization

We can rerun a saved routine in Badger. Let's rerun the `helloworld` routine that we just saved:

```shell
badger routine helloworld -r
```

Badger would behave exactly the same way as the first time you run the routine.

## View the historical optimization data

You can `cd` to the Badger archive root (the one you setup during the initial configurations) and view the historical optimization data. The file structure is a tree-like one, with year, year-month, year-month-day as the first 3 levels of branches, and the optimization runs as leaves:

```shell {4} title="Badger archive root file structure"
|--2021
    |--2021-11
        |--2021-11-24
            |--BadgerOpt-2021-11-24-133007.yaml
            |--BadgerOpt-2021-11-24-113241.yaml
            |--...
        |--...
    |--...
|--...
```

The yaml data file contains the routine information and the solutions evaluated during the run. The content would look like this:

```yaml title="BadgerOpt-2021-11-24-133007.yaml"
routine:
  name: helloworld
  algo: silly
  env: TNK
  algo_params:
    dimension: 1
    max_iter: 10
  env_params: null
  config:
    variables:
      - x2:
          - 0.0
          - 3.1416
    objectives:
      - c1: MINIMIZE
    constraints: null
data:
  timestamp:
    - 24-Nov-2021 13:30:06
    - 24-Nov-2021 13:30:06
    - 24-Nov-2021 13:30:06
    - 24-Nov-2021 13:30:06
    - 24-Nov-2021 13:30:06
    - 24-Nov-2021 13:30:06
    - 24-Nov-2021 13:30:06
    - 24-Nov-2021 13:30:07
    - 24-Nov-2021 13:30:07
    - 24-Nov-2021 13:30:07
  c1:
    - 2.093905436806936
    - 2.6185501712620036
    - -0.8170601778601619
    - 7.869183841178197
    - -1.0945113202011
    - 0.514833333947652
    - -1.0331173238615994
    - 1.4523371516674013
    - 1.3610274948700156
    - -0.0042273815683477045
  x2:
    - 1.78715008793524
    - 1.9283542649788197
    - 0.5319208795862764
    - 2.9948595695254556
    - 0.07408562477903413
    - 1.2707609271407632
    - 0.2586168520000207
    - 1.5976035652399507
    - 1.5687662333407153
    - 1.0467915830917118
```

## Create a simple environment

Now let's create a simple Badger environment and run optimization on it.

**WIP**

---
sidebar_position: 2
---

# History

Badger stores the output of every run in a collection of yaml files. You can `cd` to the Badger archive root and view the historical optimization data. The file structure is a tree-like one, with year, year-month, year-month-day as the first 3 levels of branches, and the optimization runs as leaves:

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

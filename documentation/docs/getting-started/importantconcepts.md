---
sidebar_position: 4
---

# Important concepts

Badger abstracts an optimization run as an optimization algorithm interacts with an environment, by following some pre-defined rules.[^vocs] As visualized in the picture below, the environment is controlled by the algorithm and tunes/observes the control system/machine through an interface, while the users control/monitor the optimization flow through a graphical user interface (GUI), command line interface (CLI) or application programming interface (API). Configuration settings tell Badger where plugin files are located and where optimization data should be saved. 

![Badger Environment and Interface](/img/intro/Badger-GUI.png)

Environments and interfaces in Badger are managed through a plugin system that implement how Badger interacts with the optimization probem and physical machine. Environment plugins define what parameters can be tuned and what metrics should be optimized, while interface plugins handle protocol-specific communication with hardware (EPICS, Tango, custom APIs). 
These plugins can be developed and maintained separately. 

The algorithms are provided by the Xopt package. The application interfaces (API) for creating the plugins are very straightforward and simple, yet abstractive enough to handle various situations. 

Badger offers 3 modes to satisfy different user groups:

- GUI mode, for ACR operators, enable them to perform regular optimization tasks with one click. Users can browse optimization history, configure routines, and monitor them in real-time with live plotting.
- API mode, for the algorithm developers, use the environments provided by Badger without the troubles to configure them
- CLI mode, for the command line lovers or the situation without a screen, configure and run the whole optimization in one line efficiently


![Badger architecture](/img/intro/newworkflow.png)

As shown in the Badger schematic plot above, there are several terms/concepts in Badger, and their meaning are a little different with regard to their general definitions. Let's briefly go through the terms/concepts in Badger in the following sections.

### Routine

An optimization setup in Badger is called a routine. A routine contains all the information needed to perform the optimization:

- The optimization algorithm and its hyperparameters
- The environment on which the optimization would be performed
- The configuration of the optimization, such as variables, objectives, and constraints

To run an optimization in Badger, the users need to define the routine. Badger provides several ways to easily compose the routine, so no worries, you'll not have to write it by hand:)

### Interface

An interface in Badger is a piece of code that talks to the underlying control system/machine. It communicates to the control system to:

- Set a process variable (PV) to some specific value
- Get the value of a PV

An interface is also responsible to perform the configuration needed for communicating with the control system, and the configuration can be customized by passing a `params` dictionary to the interface.

The concept of interface was introduced to Badger for better code reuse. You don't have to copy-n-paste the same fundamental code again and again when coding your optimization problems for the same underlying control system. Now you could simply ask Badger to use the same interface, and focus more on the higher level logic of the problem.

:::tip

Interfaces are **optional** in Badger -- an interface is not needed if the optimization problem is simple enough (say, analytical function) that you can directly shape it into an environment.

:::

### Environment

An environment is Badger's way to (partially) abstract an optimization problem. A typical optimization problem usually consists of the variables to tune, and the objectives to optimize. A Badger environment defines all the interested **variables** and **observations** of a control system/machine. An optimization problem can be specified by stating which variables in the environment are the variables to tune, and which observations are the objectives to optimize. Furthermore, one can define the constraints for the optimization by picking up some observation from the environment and giving it a threshold.

Take the following case as an example. Assume that we have an accelerator control system and we'd like to tune the quadupoles `QUAD:1`, `QUAD:2` and minimize the horizontal beam size on a screen `BSIZE:X`. We also want to keep the vertical beam size `BSIZE:Y` below a certain value. To do this in Badger, we could define an environment that has variables:

- `QUAD:1`
- `QUAD:2`

And observations:

- `BSIZE:X`
- `BSIZE:Y`

Then define a **[routine config](#routine-config)** to specify details of the optimization problem, as will be mentioned in the next section.

:::tip

One environment could support multiple **relevant** optimization problems -- just put all the variables and observations to the environment, and use routine config to select which variables/observations to use for the optimization.

:::

### Routine config

A routine config is the counterpart of optimization problem abstraction with regard to environment. An optimization problem can be fully defined by an environment with a routine config.

On top of the variables and observations provided by environment, routine config tells Badger which and how variables/observations are used as the tuning variables/objectives/constraints.

Use the example from the last section, the routine config for the problem could be:

```yaml title="Routine Config"
variables:
  - QUAD:1
  - QUAD:2
objectives:
  - BSIZE:X: MINIMIZE
constraints:
  - BSIZE:Y:
      - LESS_THAN
      - 0.5
```

The reasons to divide the optimization problem definition into two parts (environment and routine config) are:

- Better code reuse
- Operations in ACR usually require slightly changing a routine frequently, so it's good to have an abstraction for the frequently changed configurations (routine config), to avoid messing with the optimization source code

[^vocs]: To be more specific, the variables, objectives, constraints, and other stuff. We call it VOCS.
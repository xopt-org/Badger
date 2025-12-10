---
sidebar_position: 1
---

# Installation

Badger is essentially a python package. It's recommended to install and test it in a separate [python virtual environment](https://docs.python.org/3/library/venv.html) before using it in a production env.

## Requirements

- Python version >= 3.6. Python 3.7+ is recommended

## Install core package

Badger has a core package (`badger-opt`) that can be extended by a set of plugins. Badger core package is available on both [pip](https://pypi.org/project/badger-opt/) and [conda](https://anaconda.org/conda-forge/badger-opt). So you could install Badger with:

```shell
pip install badger-opt
```

Or

```shell
conda install -c conda-forge badger-opt
```

:::caution

If you go with the conda option and you are using macOS, the Badger GUI would need a specific version of Qt to work properly. Please run the following command in the conda env in which you installed `badger-opt`:

```shell
conda install qt=5.12.5
```

The potential GUI-not-launching issue should be gone now.

:::

## Install sample plugins

Clone the [badger plugins repo](https://github.com/slaclab/Badger-Plugins) to some directory on your computer:

```shell
git clone https://github.com/slaclab/Badger-Plugins.git
```

## Set up Badger

Once `badger-opt` is installed and you have the badger plugins ready, run the following command:

```shell
badger
```

Follow the instructions and configure several paths that are needed by Badger.

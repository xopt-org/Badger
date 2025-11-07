---
sidebar_position: 2
---

# Configuration

## Property List

#### Plugin Root

The location of custom environments and interfaces.

#### Templates Root

The location where templates for new runs are stored.

#### Logbook Root

The location where Badger run logs are stored. In some environments (e.g. LCLS/LCLS-II) these logs are added to the machine elog.

#### Archive Root

The location where old runs are archived. Runs stored here will appear in the History Navigator panel in the GUI.

---

## CLI

If you would like to change some setting that you configured after `badger` has been run for the first time, you can do so with `badger config`.

To list all the configuration properties:

```bash
badger config
```

To set a property:

```bash
badger config KEY
```

Where `KEY` is one of the keys in the configuration property list.

## GUI

The GUI includes a configuration panel as well, which may be more straightforward to use. Note that if some of these configuration properties are missing, the GUI will not launch, and you will need to set the missing property through the CLI interface.

![Badger GUI settings popup](/img/gui/settings.png)

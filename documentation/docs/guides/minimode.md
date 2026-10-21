---
sidebar_position: 9
---

# Mini Mode

Mini Mode is a simplified version of the Badger GUI designed for quick, streamlined optimization runs. It removes complexity from the full GUI by consolidating routine creation onto a single page and defaulting to automatic behavior.

## Launching Mini Mode

Launch Mini Mode from the command line:

`badger -mini`

To launch with a template preloaded:

`badger -mini -t sphere_test.yaml`

The `-t` (or `--template`) argument will look for a matching YAML template file in your configured template root directory.

:::note
The full GUI is still available via `badger -g`. The two Modes use separate UI components and do not interfere with each other.
:::

## Overview

![Mini Mode main window](/img/guides/minimode.png)

<!-- Screenshot: full Mini Mode window showing the routine page with template loaded -->

Mini Mode fits all main controls for creating and running an optimization on a single page without scrolling. The interface has two tabs:

- **Routine creation** — set up and launch a new optimization
- **History** — view and navigate past runs

## Routine Creation

### Selecting a Template

<!-- Screenshot: template dropdown at top of routine page -->
![Mini Mode template](/img/guides/minimode-template.png)

At the top of the page, a dropdown lets you select from available routine templates. When a template is loaded, it populates:

- Variables and their ranges
- Environment parameters
- Selected algorithm
- Constraints and objectives

### Environment + VOCS Tab

<!-- Screenshot: Environment + VOCS tab with algorithm selection expanded -->

![Mini Mode Environment + VOCS](/img/guides/minimode-vocs.png)


The main tab combines environment selection and VOCS configuration. Key differences from the full GUI:

- **Algorithm selection** is on this tab rather than a separate tab
- **Algorithm parameters** can be edited by expanding the "Parameters" button
- **Constraints and Observables** tables can be expanded from the bottom of the page (collapsed by default)

### Variable Table

<!-- Screenshot: variable table showing Saved, Current, and Range columns -->

![Mini Mode Variable Table](/img/guides/minimode-variable.png)

The variable table displays three key columns instead of raw upper/lower bounds:

| Column | Description |
|--------|-------------|
| **Saved** | The value variables will be reset to if you press reset. Updates each time a new run starts. |
| **Current** | Live value read from the environment. Updates when Badger writes to variables (dial in, reset, or at each optimization step), or when the table is manually refreshed. |
| **Range** | Shown as a delta (±) around the current value. Based on the selected range option from the template. |

#### Range Indicators

- If desired bounds are clipped by hard variable limits, an **asterisk (*)** appears next to the range value.
- Selected variable rows appear with **lighter text**; unselected rows use **darker gray text**.

#### Adjusting Ranges

<!-- Screenshot: variable table with range adjustment arrows highlighted -->

- Use the **up/down arrows** on each row to adjust the range for that variable
- Use the arrows in the **header row** to adjust ranges for all selected variables at once
- Up scales the range by 1.111×; down scales by 0.9× (ranges adjust proportionally)
- Click the **gear icon** on a row for more detailed range control via the variable range dialog

#### Show Checked Only

When "Show checked only" is unchecked, the table scrolls to display the first selected row.

### Variable Range Dialog

<!-- Screenshot: individual variable range dialog with bounds preview bar -->
![Mini Mode Variable Dialog](/img/guides/minimode-variable-dialog.png)

Clicking the gear icon on a variable row opens a dialog with:

- The current value of the variable
- The current low and high bounds for the variable
- Options for range selection method
    - ratio wrt current value: Bounds are calculated as a fraction of the current value on either side of the current value
    - ratio wrt full range: Bounds are calculated as a fraction of the full range on either side of the current value
    - delta around current value: Bounds are calculated as a delta on either side of the current value
    - exact bounds: the input numerical bounds are used.
- A **bounds preview bar** showing what the resulting bounds will be
- Hard limits displayed (but not editable)

### Initial Points

<!-- Screenshot: initial points section collapsed -->
![Mini Mode Initial Points](/img/guides/minimode-initialpoints.png)

Initial points selection is collapsed by default. Points are automatically chosen from within a subset of the configured variable range.

## Running an Optimization

Mini Mode defaults to automatic behavior — there is no manual/automatic Mode toggle. Once your routine is configured:

1. Select or load a template
2. Verify variables, ranges, and objectives
3. Start the run

Variable ranges are automatically set around the current value based on template parameters.

Mini Mode uses a **smart run controller** that combines play, pause, resume, and restart into a single button. There is no separate pause button — the primary action button changes behavior based on the current routine state and whether you have edited any parameters since the run started. 

<!-- Screenshot: minimode-run-idle.png — run button with dropdown expanded -->
  ![Mini Mode run controls](/img/guides/minimode-run-idle.png)

  ### Play Button Behavior

  The play button adapts to context:
  | State | Button action | What happens |
|-------|---------------|--------------|
| Stopped | **Start** | Launches the routine with the current configuration |
| Running | **Pause** | Suspends the optimization loop; subprocess state is preserved |
| Paused, no changes | **Resume** | Continues from where the routine paused |
| Paused, compatible edits (e.g., range changes) | **Reload & resume** | Stops the subprocess, reloads data, and restarts with the new settings |
| Paused, structural edits (variables/objectives changed) | **Restart** | Fully restarts the routine with the new VOCS |

  The controller decides which branch to take by comparing the current GUI
  state against the snapshot of the routine that is actively displayed, so
  you can tweak ranges or algorithm parameters mid-session without manually
  restarting.

  ### Termination Conditions
  
  <!-- Screenshot: minimode-run-running.png — play button with duration indicator -->
  ![Mini Mode run button during a run](/img/guides/minimode-run-running.png)

  The current termination condition is shown directly on the play button as a duration or iteration indicator. Each time you press play, the termination condition is extended, so pressing play repeatedly gives you a consistent "N more iterations per press" behavior rather than resuming indefinitely.

  ### Run Menu
  
  The dropdown next to the play button exposes two actions:

  - **New Run** — forces a fresh routine regardless of current state. Use this when you want to discard the current session and start over.
  - **Edit Condition** — opens a dialog to configure the termination condition (iteration count, time limit, etc.) without starting a new run. Changes take effect the next time you press play.

  <!-- Screenshot: minimode-edit-condition.png — Edit Condition dialog -->
  ![Edit termination condition dialog](/img/guides/minimode-edit-condition.png)
  
  ### Pause/Resume Details

  - Pausing waits for the subprocess to acknowledge before updating the status bar — the "Routine *name* paused" message appears only once the subprocess has actually suspended, so the UI never falsely reports a pause that has not yet taken effect.
  - The last sampled point is displayed correctly when a run pauses (previously the UI could lag by one step).
  - Closing the Mini Mode window while a routine is running or paused terminates the subprocess cleanly rather than leaving it orphaned.

## History Tab

<!-- Screenshot: history tab showing past runs -->
![Mini Mode History Tab](/img/guides/minimode-history.png)

The History tab lets you browse and load past optimization runs, similar to the History Navigator in the full GUI.

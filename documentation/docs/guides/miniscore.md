---
sidebar_position: 7
---

# MiniSCORE (Checkpoints)

The MiniSCORE feature is composed of a flag button on the run buttons strip, as
well as a dropdown from this button. The feature is used to store the current
state of an environment's variables, edit the saved state, and then apply the
saved state to the environment's variables again.

- Clicking the flag button on the run buttons strip, or entering the dropdown and
  selecting the "Save Checkpoint" option, will save the current environment's
  variables to memory.
- Entering the dropdown and selecting the "Edit Checkpoint" option will display
  a popup from which the saved state can be edited. Selecting "OK" on this popup
  will save the displayed state back to memory, and selecting "Cancel" will undo
  all changes. The popup will display a table of values: the first column represents
  the variable name, the second column is the current value of the variable, and the
  third editable column is the stored value of the variable in Badger memory.

  ![Badger MiniSCORE checkpoint editor window](/img/gui/miniscore.png)
- Entering the dropdown and selecting the "Load Checkpoint" option will load the
  stored variables back into the current environment.

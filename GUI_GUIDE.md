# Main Interface Layout

![Layout](pics/layout.png)

## Bottom Region

### Status Bar
- **File**: `src/badger/gui/default/components/status_bar.py`
- **Screenshot**: ![Status Bar](pics/status_bar.png)
- **Description**: Bottom status bar displaying optimization summary with eliding text label and settings button (gear icon) that launches the BadgerSettingsDialog.

## Top Region Layout

### Left Side - History Navigator

- **File**: `src/badger/gui/acr/components/history_navigator.py`
- **Screenshot**: ![History Navigator](pics/history_navigator.png)
- **Description**: Tree-based browser for archived optimization runs with date-based organization, inherits from default history navigator with bold header styling.

### Right Top Section - Left: Routine Configuration

#### Routine Editor
- **File**: `src/badger/gui/acr/components/routine_editor.py`
- **Description**: Legacy code, can be removed

#### Routine Page (Sub-component)
- **File**: `src/badger/gui/acr/components/routine_page.py`
- **Screenshot**: ![Routine Page Tabs](pics/routine_page.png)
- **Description**: Comprehensive optimization configuration interface with multiple tabs (metadata, env + vocs, algorithm) containing all optimization settings.

#### Environment + Variables/Objectives/Constraints/Observables Tab Details

#### Auto/Manual Mode Toggle
- **File**: `src/badger/gui/acr/components/env_cbox.py:268`
- **Screenshot**: ![Auto Manual Toggle](pics/auto_manual_toggle.png)
- **Description**: QCheckBox labeled "Automatic" that controls variable range and initial point behavior - when enabled, locks bounds for auto-calculation; when disabled, allows manual editing.

#### Variable Table with Add New Variable
- **File**: `src/badger/gui/default/components/var_table.py` (VariableTable class)
- **Screenshot**: ![Variable Table](pics/variable_table.png)
- **Description**: Custom variable configuration table with drag-drop support and context menu for adding variables, uses different architecture than other tables with specialized variable management.

#### Add New Objective/Constraint/Observable Tables
- **Files**:
  - `src/badger/gui/default/components/obj_table.py` (ObjectiveTable)
  - `src/badger/gui/default/components/con_table.py` (ConstraintTable)
  - `src/badger/gui/default/components/obs_table.py` (ObservableTable)
- **Screenshot**: ![Objective Table](pics/obj_table.png)
![Constraint Table](pics/con_table.png)
![Observable Table](pics/obs_table.png)
- **Description**: All inherit from EditableTable base class with drag-drop text functionality for adding new entries, sharing common architecture unlike variable table.

### Right Top Section - Run Monitor

- **File**: `src/badger/gui/default/components/run_monitor.py`
- **Screenshot**: ![Run Monitor](pics/run_monitor.png)
- **Description**: Primary optimization monitoring interface with live PyQtGraph plots for variables, objectives, and constraints, includes collapsible data table drawer at bottom.

#### Data Table Drawer
- **File**: `src/badger/gui/default/components/data_table.py`
- **Screenshot**: ![Data Table Drawer](pics/data_table_drawer.png)
- **Description**: Collapsible table view within run monitor showing optimization results with copy/paste functionality and alternating row styling.

### Right Bottom Section: Action Bar

- **File**: `src/badger/gui/acr/components/action_bar.py`
- **Screenshot**: ![Action Bar](pics/action_bar.png)
- **Description**: Centralized control panel with comprehensive optimization and environment management buttons.

#### Run Button (Overloaded)
- **Implementation**: QToolButton with dropdown menu
- **Screenshot**: ![Run Button Dropdown](pics/run_button_dropdown.png)
- **Features**:
  - **Run**: Start optimization routine
  - **Run Until**: Run with stopping condition
  - **Stop**: Terminate running optimization
  - **Multi-state**: Button text/icon changes based on optimization state

#### Environment Control Buttons
- **Screenshot**: ![Environment Controls](pics/environment_controls.png)
- **Buttons**:
  - **Reset Environment**: Reset system to initial state
  - **Jump to Optimum**: Move to best found solution
  - **Dial In**: Apply current variable values to system

#### Management Buttons
- **Screenshot**: ![Management Buttons](pics/management_buttons.png)
- **Buttons**:
  - **Delete Run**: Remove selected optimization run
  - **Logbook**: Access optimization logbook
  - **Pause/Resume**: Pause or resume running optimization
  - **Extensions**: Launch extensions palette

# Dialog Windows & Popups (refined for ACR)

## Settings Dialog
- **File**: `src/badger/gui/acr/windows/settings_dialog.py`
- **Screenshot**: ![Settings Dialog](pics/settings_dialog.png)
- **Description**: Application configuration dialog for root paths (plugin, template, logbook, archive), extends QDialog and launched from status bar settings button.

## Individual Variable Range Dialog
- **File**: `src/badger/gui/acr/windows/ind_lim_vrange_dialog.py`
- **Screenshot**: ![Individual Variable Range Dialog](pics/ind_var_range_dialog.png)
- **Description**: Configure optimization limits for single variables with ratio/delta options using QStackedWidget for different parameter input modes (ratio wrt current, ratio wrt range, delta around current).

## Archive Search Widget
- **File**: `src/badger/gui/acr/components/archive_search.py`
- **Screenshot**: ![Archive Search](pics/archive_search.png)
- **Description**: Search and browse variables from archive systems (e.g., EPICS archiver) with drag-and-drop support for variable selection, launched from routine page PV button.

# Reused Default GUI Dialogs

## Scrollable Message Box (Error Dialog)
- **File**: `src/badger/gui/default/windows/message_dialog.py` (BadgerScrollableMessageBox)
- **Screenshot**: ![Error Message Dialog](pics/error_message_dialog.png)
- **Description**: Error display with scrollable detailed text area and monospace formatting, used in both home_page and routine_page for exception handling.

## Batch Variable Range Dialog
- **File**: `src/badger/gui/default/windows/lim_vrange_dialog.py` (BadgerLimitVariableRangeDialog)
- **Screenshot**: ![Batch Variable Range Dialog](pics/batch_var_range_dialog.png)
- **Description**: Set variable ranges for multiple variables simultaneously with "Apply to All Variables" vs "Only Visible" radio button options.

## Add Random Variables Dialog
- **File**: `src/badger/gui/default/windows/add_random_dialog.py` (BadgerAddRandomDialog)
- **Screenshot**: ![Add Random Dialog](pics/add_random_dialog.png)
- **Description**: Dialog for adding random initial points to optimization routine, launched from routine page add random button.

## Documentation Dialogs

### Generator Documentation Window
- **File**: `src/badger/gui/default/windows/docs_window.py` (BadgerDocsWindow)
- **Screenshot**: ![Generator Docs](pics/generator_docs.png)
- **Description**: Display documentation for selected optimization generator/algorithm, launched from generator selection dropdown in routine configuration.

### Environment Documentation Window
- **File**: `src/badger/gui/default/windows/env_docs_window.py` (BadgerEnvDocsWindow)
- **Screenshot**: ![Environment Docs](pics/environment_docs.png)
- **Description**: Display documentation for selected optimization environment, launched from environment selection dropdown in routine configuration.

# Extension System

## Extensions Palette
- **File**: `src/badger/gui/default/components/extensions_palette.py`
- **Screenshot**: ![Extensions Palette](pics/extensions_palette.png)
- **Description**: Manager window for launching specialized analysis tools, displays available extensions with buttons and tracks active extension count.

### Pareto Front Viewer
- **File**: `src/badger/gui/default/components/pf_viewer/pf_widget.py`
- **Screenshot**: ![Pareto Front Viewer](pics/pareto_front_viewer.png)
- **Description**: Multi-objective optimization analysis extension with Pareto front visualization, hypervolume tracking, and variable/objective space plotting capabilities.

### Bayesian Optimization Visualizer
- **File**: `src/badger/gui/default/components/bo_visualizer/bo_widget.py`
- **Screenshot**: ![BO Visualizer](pics/bo_visualizer.png)
- **Description**: Advanced Bayesian optimization analysis tool for visualizing Gaussian Process models, acquisition functions, and optimization landscapes with variable selection and reference point setting.

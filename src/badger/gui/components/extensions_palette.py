"""Launcher panel listing available analysis extensions (BO Visualizer,
Pareto Front Viewer) with buttons to open each in its own window."""

import traceback
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from badger.gui.components.analysis_extensions import (
    AnalysisExtension,
    BaxVisualizer,
    BOVisualizer,
    ParetoFrontViewer,
)
from badger.gui.components.extension_utilities import HandledException

if TYPE_CHECKING:
    from badger.gui.components.run_monitor import BadgerOptMonitor


class ExtensionsPalette(QMainWindow):
    """
    A QMainWindow-based user interface for managing and launching extensions in Badger.

    Parameters
    ----------
    run_monitor : BadgerOptMonitor
        The run monitor associated with the palette.

    Attributes
    ----------
    base_text : str
        Base text for the number of active extensions.
    text_box : QLabel
        QLabel widget for displaying the number of active extensions.
    btn_data_viewer : QPushButton
        QPushButton for launching the ParetoFrontViewer extension.

    Methods
    -------
    n_active_extensions
        Property to get the number of active extensions.
    update_palette
        Update the display of the active extensions count.
    add_pf_viewer
        Open the ParetoFrontViewer extension.
    add_child_window_to_monitor(child_window)
        Add a child window to the run monitor.

    """

    def __init__(self, run_monitor: "BadgerOptMonitor") -> None:
        """
        Initialize the ExtensionsPalette.

        Parameters
        ----------
        run_monitor : BadgerOptMonitor
            The run monitor associated with the palette.

        """
        super().__init__(parent=run_monitor)

        self.run_monitor = run_monitor

        self.setWindowTitle("Badger Extensions Palette")
        self.resize(320, 240)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        self.base_text = "Number of active exensions: "
        self.text_box = QLabel(self.base_text + "0", self)
        self.text_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.text_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_data_viewer = QPushButton("Pareto Front Viewer")
        self.btn_bo_visualizer = QPushButton("Bayesian Optimization Visualizer")
        self.btn_bax_visualizer = QPushButton("Bax Visualizer")

        layout.addWidget(self.btn_data_viewer)
        layout.addWidget(self.btn_bo_visualizer)
        layout.addWidget(self.btn_bax_visualizer)
        layout.addStretch()
        layout.addWidget(self.text_box)

        central_widget.setLayout(layout)

        self.btn_data_viewer.clicked.connect(self.add_pf_viewer)
        self.btn_bo_visualizer.clicked.connect(self.add_bo_visualizer)
        self.btn_bax_visualizer.clicked.connect(self.add_bax_visualizer)

    @property
    def n_active_extensions(self) -> int:
        """
        Property to get the number of active extensions.

        Returns
        -------
        int
            The number of active extensions.

        """
        return len(self.run_monitor.active_extensions)

    def update_palette(self) -> None:
        self.text_box.setText(self.base_text + str(self.n_active_extensions))

    def add_pf_viewer(self) -> None:
        """
        Open the ParetoFrontViewer extension.

        """
        if self.run_monitor.routine is None:
            QMessageBox.warning(
                self,
                "No Routine Error",
                "Please start a routine before opening the Pareto Front Viewer.",
            )
            return

        self.add_child_window_to_monitor(
            ParetoFrontViewer(routine=self.run_monitor.routine, parent=self)
        )

    def add_bo_visualizer(self) -> None:
        """
        Open the BOVisualizer extension.

        """
        if self.run_monitor.routine is None:
            QMessageBox.warning(
                self,
                "No Routine Error",
                "Please start a routine before opening the BO Visualizer.",
            )
            return

        self.add_child_window_to_monitor(
            BOVisualizer(routine=self.run_monitor.routine, parent=self)
        )

    def add_bax_visualizer(self) -> None:
        """
        Open the BaxVisualizer extension.

        """
        if self.run_monitor.routine is None:
            QMessageBox.warning(
                self,
                "No Routine Error",
                "Please start a routine before opening the Bax Visualizer.",
            )
            return

        self.add_child_window_to_monitor(
            BaxVisualizer(routine=self.run_monitor.routine, parent=self)
        )

    def add_child_window_to_monitor(self, child_window: AnalysisExtension) -> None:
        """
        Add a child window to the run monitor.

        Parameters
        ----------
        child_window : AnalysisExtension
            The child window (extension) to add to the run monitor.

        """
        child_window.window_closed.connect(self.run_monitor.extension_window_closed)
        self.run_monitor.active_extensions.append(child_window)

        try:
            if self.run_monitor.routine is not None:
                child_window.update_window(self.run_monitor.routine)

            child_window.show()
            self.update_palette()
        except HandledException as e:
            QMessageBox.critical(self, "Handled Exception Error", str(e))
        except Exception:
            QMessageBox.critical(
                self, "Unhandled Exception Error", traceback.format_exc()
            )

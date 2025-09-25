import traceback

from PyQt5.QtWidgets import (
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
    QMessageBox,
    QSizePolicy,
)
from PyQt5.QtCore import Qt
from badger.gui.components.analysis_extensions import (
    AnalysisExtension,
    ParetoFrontViewer,
    BOVisualizer,
)
from badger.gui.components.extension_utilities import HandledException


class ExtensionsPalette(QMainWindow):
    """
    A QMainWindow-based user interface for managing and launching extensions in Badger.

    Parameters
    ----------
    run_monitor : RunMonitor
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

    def __init__(self, run_monitor):
        """
        Initialize the ExtensionsPalette.

        Parameters
        ----------
        run_monitor : RunMonitor
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

        layout.addWidget(self.btn_data_viewer)
        layout.addWidget(self.btn_bo_visualizer)
        layout.addStretch()
        layout.addWidget(self.text_box)

        central_widget.setLayout(layout)

        self.btn_data_viewer.clicked.connect(self.add_pf_viewer)
        self.btn_bo_visualizer.clicked.connect(self.add_bo_visualizer)

    @property
    def n_active_extensions(self):
        """
        Property to get the number of active extensions.

        Returns
        -------
        int
            The number of active extensions.

        """
        return len(self.run_monitor.active_extensions)

    def update_palette(self):
        self.text_box.setText(self.base_text + str(self.n_active_extensions))

    def add_pf_viewer(self):
        """
        Open the ParetoFrontViewer extension.

        """
        self.add_child_window_to_monitor(ParetoFrontViewer())

    def add_bo_visualizer(self):
        """
        Open the BOVisualizer extension.

        """
        self.add_child_window_to_monitor(BOVisualizer())

    def add_child_window_to_monitor(self, child_window: AnalysisExtension):
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

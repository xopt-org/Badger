from dataclasses import dataclass
from types import NoneType
from typing import Optional, Any, get_origin, Union, get_args

from pydantic_core import PydanticUndefined
import yaml
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QLineEdit,
    QLabel,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QDialog,
    QDialogButtonBox,
    QScrollArea,
    QHBoxLayout,
    QStackedWidget,
    QComboBox,
)
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from xopt.generators import get_generator
from xopt.generators.bayesian.expected_improvement import ExpectedImprovementGenerator
from xopt.generators.bayesian.turbo import TurboController

import logging

logger = logging.getLogger(__name__)

# Removes sub-parameters from the main editor view by default
USE_CONFIGURE_BUTTONS = False


@dataclass
class BadgerResolvedType:
    main: type[Any] | None = None
    nullable: bool = False
    subtype: Optional["BadgerResolvedType | list[BadgerResolvedType]"] = None

    @classmethod
    def find_primary(
        cls, annotations: list[Any] | tuple[Any, ...]
    ) -> Optional["BadgerResolvedType"]:
        if len(annotations) == 0:
            return None

        resolved = [
            BadgerResolvedType.resolve(annotation) for annotation in annotations
        ]
        for r in resolved:
            if r.main is None:
                continue
            if issubclass(r.main, BaseModel):
                return r

        priority: list[type] = [dict, list, str, float, int, bool]
        for p in priority:
            for r in resolved:
                if p == r.main:
                    return r

        return resolved[0]

    @classmethod
    def resolve(
        cls, annotation: type[Any] | Union[Any, None] | None
    ) -> "BadgerResolvedType":
        origin: type[Any] | Union[Any, None] | None = get_origin(annotation)
        args = get_args(annotation)
        nullable = False

        if origin is None:
            origin = annotation

        if len(args) == 0:
            return BadgerResolvedType(main=annotation)

        if origin == Union:
            if NoneType in args:
                origin = Optional
                args = [arg for arg in args if arg != NoneType]
            else:
                if len(args) == 1:
                    origin = args[0]
                    args = []
                    nullable = True

                    if origin is not None:
                        resolved = BadgerResolvedType.resolve(origin)
                        resolved.nullable = True
                        return resolved
                elif len(args) > 1:
                    primary = BadgerResolvedType.find_primary(args)
                    return BadgerResolvedType(
                        main=origin,
                        nullable=nullable,
                        subtype=primary,
                    )

        if origin == Optional:
            origin = args[0]
            args = []
            nullable = True

            if origin is not None:
                resolved = BadgerResolvedType.resolve(origin)
                resolved.nullable = True
                return resolved

        # Dicts have two subtypes, special case
        if origin is dict:
            if len(args) == 2:
                return BadgerResolvedType(
                    main=origin,
                    subtype=[BadgerResolvedType.resolve(arg) for arg in args],
                )
            return BadgerResolvedType(main=str)

        return BadgerResolvedType(
            main=origin,
            nullable=nullable,
            subtype=BadgerResolvedType.find_primary(args),
        )

    @classmethod
    def resolve_qt(
        cls,
        annotation: type[Any] | Union[Any, None] | None,
        default: float | int | bool | None = None,
        recursive: bool = False,
    ):
        resolved_type = BadgerResolvedType.resolve(annotation)
        widget = QLabel()

        if resolved_type.main is None:
            widget = QLineEdit()
            widget.setText("null")
        elif issubclass(resolved_type.main, BaseModel):
            if issubclass(resolved_type.main, TurboController):
                widget = BadgerPydanticEditor()
                # widget.addItem("optimize")
                # widget.addItem("safety")
            elif recursive:
                return None  # None means add children to the tree
            else:
                widget = BadgerPydanticConfigureButton(
                    resolved_type.main, BadgerPydanticConfigureDialog
                )
        elif resolved_type.main == NoneType:
            widget = QLabel()
            widget.setText("null")
        elif resolved_type.main is dict:
            if resolved_type.subtype is None:
                widget = QLabel()
                widget.setText("null")
            elif isinstance(resolved_type.subtype, list):
                primary = resolved_type.subtype[0].main
                secondary = resolved_type.subtype[1].main
                if primary is not None:
                    widget = BadgerListEditor(primary, secondary)
                else:
                    widget = QLabel()
                    widget.setText("null")
            else:
                primary = resolved_type.subtype
                if primary.main is not None:
                    widget = BadgerListEditor(primary.main)
                else:
                    widget = QLabel()
                    widget.setText("null")
        elif resolved_type.main is list:
            if resolved_type.subtype is None:
                widget = QLabel()
                widget.setText("null")
            elif isinstance(resolved_type.subtype, list):
                primary = resolved_type.subtype[0].main
                secondary = resolved_type.subtype[1].main
                if primary is not None:
                    widget = BadgerListEditor(primary, secondary)
                else:
                    widget = QLabel()
                    widget.setText("null")
            else:
                primary = resolved_type.subtype
                if primary.main is not None:
                    widget = BadgerListEditor(primary.main)
                else:
                    widget = QLabel()
                    widget.setText("null")
        elif resolved_type.main is float:
            widget = QDoubleSpinBox()
            widget.setRange(float("-inf"), float("inf"))
            widget.setValue(float(default) if default is not None else 0.0)
        elif resolved_type.main is int:
            widget = QSpinBox()
            widget.setRange(-(2**31), 2**31 - 1)  # int32 min/max
            widget.setValue(int(default) if default is not None else 0)
        elif resolved_type.main is bool:
            widget = QCheckBox()
            widget.setChecked(bool(default) if default is not None else False)
        else:
            widget = QLineEdit()
            if default is None:
                widget.setText("null")
            else:
                widget.setText(str(default))

        widget.setProperty("badger_nullable", resolved_type.nullable)
        return widget


def _qt_widget_to_yaml_value(widget: Any) -> str | None:
    if isinstance(widget, QTreeWidget):
        return None
    elif isinstance(widget, BadgerPydanticConfigureButton):
        parameters = widget.get_parameters()
        if len(parameters) == 0:
            if widget.property("badger_nullable"):
                return "null"
            else:
                return "{}"
        else:
            return widget.get_parameters()
    elif isinstance(widget, BadgerListEditor):
        return widget.get_parameters()
    elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
        return str(widget.value())
    elif isinstance(widget, QCheckBox):
        return "true" if widget.isChecked() else "false"
    elif isinstance(widget, QComboBox):
        return '"' + widget.currentText() + '"'
    elif isinstance(widget, (QLabel, QLineEdit)):
        if widget.text() == "null" or widget.text() == "None":
            return "null"
        else:
            return (
                ('"' + widget.text() + '"')
                if isinstance(widget, QLineEdit)
                else widget.text()
            )
    return "null"


def _qt_widgets_to_yaml_recurse(
    table: QTreeWidget, item: QTreeWidgetItem | None
) -> str:
    out: str = "{"
    if item is None:
        return out + "}"
    for i in range(item.childCount()):
        tree_item = item.child(i)
        if tree_item is None:
            continue
        out += f'"{tree_item.text(0)}":'
        widget = table.itemWidget(tree_item, 1)
        if widget is None:
            if tree_item.childCount() > 0:
                out += _qt_widgets_to_yaml_recurse(table, tree_item)
            else:
                out += "null"
        else:
            value = _qt_widget_to_yaml_value(widget)
            out += value if value is not None else "null"
        if i < item.childCount() - 1:
            out += ","
    out += "}"
    return out


class BadgerListItem(QWidget):
    def __init__(
        self,
        widget_type: type[Any],
        widget_type2: type[Any] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.parameter_value = BadgerResolvedType.resolve_qt(widget_type)
        layout.addWidget(self.parameter_value)
        self.parameter_value2 = None
        if widget_type2 is not None:
            self.parameter_value2 = BadgerResolvedType.resolve_qt(widget_type2)
            layout.addWidget(self.parameter_value2)
        remove_button = QPushButton("Remove")
        remove_button.setFixedWidth(85)
        remove_button.clicked.connect(self.remove)
        layout.addWidget(remove_button, Qt.AlignmentFlag.AlignRight)

    def remove(self):
        self.setParent(None)
        self.deleteLater()


class BadgerListEditor(QWidget):
    def __init__(
        self,
        widget_type: type[Any],
        widget_type2: type[Any] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.widget_type = widget_type
        self.widget_type2 = widget_type2

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)

        scroll = QScrollArea()
        scroll.setMinimumHeight(64)
        scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)

        add_button = QPushButton("Add")
        add_button.setFixedWidth(90)
        add_button.clicked.connect(self.add_widget)
        layout.addWidget(add_button)

    def add_widget(self):
        self.list_layout.addWidget(BadgerListItem(self.widget_type, self.widget_type2))

    def get_parameters(self):
        child_values: list[str | None] = [
            _qt_widget_to_yaml_value(child.parameter_value)
            for child in self.list_container.children()
            if isinstance(child, BadgerListItem)
        ]
        if len(child_values) == 0 and self.property("badger_nullable"):
            return "null"

        if self.widget_type2 is None:
            values = [value for value in child_values if value is not None]
            return "[" + ",".join(values) + "]"
        else:
            child_values2 = [
                _qt_widget_to_yaml_value(child.parameter_value2)
                for child in self.list_container.children()
                if isinstance(child, BadgerListItem)
            ]
            return (
                "{"
                + ",".join(
                    [str(k) + ":" + str(v) for k, v in zip(child_values, child_values2)]
                )
                + "}"
            )


class BadgerPydanticConfigureDialog(QDialog):
    def __init__(self, model_type: type[Any], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Badger - " + model_type.__name__)
        self.setMinimumSize(450, 450)
        layout = QVBoxLayout(self)
        self.editor = BadgerPydanticEditor(self, recursive=True)
        self.editor.set_params_from_class(model_type)
        layout.addWidget(self.editor)
        self.buttons = QDialogButtonBox(self)
        self.buttons.setStandardButtons(QDialogButtonBox.StandardButton.Ok)
        self.buttons.accepted.connect(self.hide)
        layout.addWidget(self.buttons)

    def get_parameters(self):
        return self.editor.get_parameters()


class BadgerPydanticConfigureButton(QWidget):
    def __init__(
        self,
        model_type: type[Any],
        dialog_type: type[BadgerPydanticConfigureDialog],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        self.button = QPushButton()
        layout.addWidget(self.button)
        self.button.setText("Configure")
        self.button.setFixedWidth(90)
        self.dialog = dialog_type(model_type)
        self.button.clicked.connect(self.activate_dialog)

    def activate_dialog(self):
        self.dialog.show()

    def get_parameters(self):
        return self.dialog.editor.get_parameters()


class BadgerPydanticEditor(QTreeWidget):
    def __init__(
        self,
        parent: QTreeWidget | None = None,
        recursive: bool = (not USE_CONFIGURE_BUTTONS),
    ):
        QTreeWidget.__init__(self, parent)
        self.setColumnCount(2)
        self.setColumnWidth(0, 200)
        self.setHeaderLabels(["Parameter", "Value"])

        self.model_class = None
        self.recursive = recursive

    def _set_params_recurse(
        self, parent: Optional[QTreeWidgetItem], fields: dict[str, FieldInfo]
    ):
        for field_name, field_info in fields.items():
            child = QTreeWidgetItem([field_name, ""])
            if parent is None:
                self.addTopLevelItem(child)
            else:
                parent.addChild(child)
            child.setToolTip(0, field_info.description)

            widget = BadgerResolvedType.resolve_qt(
                annotation=field_info.annotation,
                default=field_info.default,
                recursive=self.recursive,
            )
            if widget is None:
                resolved = BadgerResolvedType.resolve(field_info.annotation)
                if self.recursive:
                    if resolved.main is not None:
                        self._set_params_recurse(child, resolved.main.model_fields)
                    else:
                        raise ValueError("Unable to resolve model fields")
                continue
            self.setItemWidget(child, 1, widget)

    def set_params_from_class(self, pydantic_class: type[Any]):
        self.clear()
        self.model_class = pydantic_class
        self._set_params_recurse(None, self.model_class.model_fields)

    def set_params_from_generator(self, generator_name: str, defaults: dict[str, Any]):
        self.clear()
        self.model_class = get_generator(generator_name)
        # print(defaults)
        self._set_params_recurse(
            None,
            {k: v for k, v in self.model_class.model_fields.items() if k in defaults},
        )
        # Update parameters with defaults from generator class
        if issubclass(self.model_class, ExpectedImprovementGenerator):
            turbo_controller_options = (
                self.model_class.get_compatible_turbo_controllers()
            )
            if turbo_controller_options:
                logger.debug(
                    f"Using turbo controller options: {turbo_controller_options}"
                )

                turbo_controller_items = self.findItems(
                    "turbo_controller", Qt.MatchFlag.MatchExactly
                )
                if turbo_controller_items:
                    turbo_controller_item = turbo_controller_items[0]
                    widget = self.itemWidget(turbo_controller_item, 1)
                    if widget and isinstance(widget, QComboBox):
                        option_names = [
                            option.__name__ for option in turbo_controller_options
                        ]

                        simple_widget = QComboBox()
                        simple_widget.addItems(option_names)

                        # Create detailed widget from default pydantic params
                        detailed_widget = BadgerResolvedType.resolve_qt(
                            annotation=turbo_controller_options[0],
                            recursive=True,
                        )

                        toggle_widget = ToggleDetailWidget(
                            simple_widget, detailed_widget
                        )
                        self.setItemWidget(turbo_controller_item, 1, toggle_widget)

                    # defaults = self.get_defaults_from_type(SafetyTurboController)

                    # logger.debug(f"Using turbo controller defaults: {defaults}")

    @staticmethod
    def get_defaults_from_type(pydantic_class: type[Any]):
        if not issubclass(pydantic_class, BaseModel):
            raise ValueError("Provided class is not a Pydantic model")
        defaults: dict[str, Any] = {}
        for field_name, field_info in pydantic_class.model_fields.items():
            if field_info.default is not PydanticUndefined:
                defaults[field_name] = field_info.default
            elif field_info.default_factory is not None:
                defaults[field_name] = field_info.default_factory()
        return defaults

    def get_parameters(self):
        # print(_qt_widgets_to_yaml_recurse(self, self.invisibleRootItem()))
        return _qt_widgets_to_yaml_recurse(self, self.invisibleRootItem())

    def validate(self):
        if self.model_class is None:
            return True
        return self.model_class.model_validate(yaml.safe_load(self.get_parameters()))


class ToggleDetailWidget(QWidget):
    def __init__(
        self,
        simple_widget: QWidget,
        detailed_widget: QWidget,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.is_detailed = False

        self.stack = QStackedWidget()
        self.simple_widget = simple_widget
        self.detailed_widget = detailed_widget

        self.stack.addWidget(simple_widget)
        self.stack.addWidget(detailed_widget)
        self.stack.setCurrentIndex(0)

        self.button = QPushButton("Show More")
        self.button.clicked.connect(self.swapLayout)

        self.initLayout()

    def initLayout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.stack)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def swapLayout(self):
        if self.is_detailed:
            self.stack.setCurrentIndex(0)
            self.button.setText("Show More")
            self.is_detailed = False
        else:
            self.stack.setCurrentIndex(1)
            self.button.setText("Show Less")
            self.is_detailed = True

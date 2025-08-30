from dataclasses import dataclass
from types import NoneType
from typing import Optional, Any, get_origin, Union, get_args, Self

import yaml
from PyQt5.QtCore import Qt, pyqtSignal
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
    QScrollArea,
    QHBoxLayout,
    QComboBox,
)
from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo
from xopt.generator import Generator
from xopt.generators import get_generator
from xopt.generators.bayesian.turbo import (
    TurboController,
    OptimizeTurboController,
    SafetyTurboController,
    EntropyTurboController,
)
from xopt.numerical_optimizer import NumericalOptimizer, LBFGSOptimizer, GridOptimizer


def _set_value_for_basic_widget(
    widget: QLabel | QDoubleSpinBox | QSpinBox | QCheckBox | QLineEdit,
    value: str | float | int | bool | None,
):
    if isinstance(widget, QLabel) or isinstance(widget, QLineEdit):
        widget.setText("null" if value is None else str(value))
    elif isinstance(widget, QDoubleSpinBox):
        widget.setValue(float(value))
    elif isinstance(widget, QSpinBox):
        widget.setValue(int(value))
    elif isinstance(widget, QCheckBox):
        widget.setChecked(bool(value))


@dataclass
class BadgerResolvedType:
    main: Any = None
    nullable: bool = False
    subtype: Optional[Self | list[Self]] = None

    @classmethod
    def find_primary(cls, annotations: list[Any]) -> Optional[Self]:
        if len(annotations) == 0:
            return None

        resolved = [
            BadgerResolvedType.resolve(annotation) for annotation in annotations
        ]
        for r in resolved:
            if issubclass(r.main, BaseModel):
                return r

        priority = [dict, list, str, float, int, bool]
        for p in priority:
            for r in resolved:
                if p == r.main:
                    return r

        return resolved[0]

    @classmethod
    def resolve(cls, annotation) -> Self:
        origin = get_origin(annotation)
        args = get_args(annotation)
        nullable = False

        if origin is None:
            origin = annotation
        if len(args) == 0:
            return BadgerResolvedType(main=annotation)

        if origin == Union:
            if len(args) == 1:
                origin = args[0]
                args = []
            elif NoneType in args:
                origin = Optional
                args = [arg for arg in args if arg != NoneType]

            if len(args) > 1:
                return BadgerResolvedType.find_primary(args)

        if origin == Optional:
            origin = args[0]
            args = []
            nullable = True

            if get_origin(origin) is not None:
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
        annotation,
        default,
        editor_info: tuple["BadgerPydanticEditor", QTreeWidgetItem] | None = None,
    ):
        resolved_type = BadgerResolvedType.resolve(annotation)
        if issubclass(resolved_type.main, BaseModel):
            if issubclass(resolved_type.main, TurboController):
                # hack: replace this?
                types = [
                    OptimizeTurboController,
                    SafetyTurboController,
                    EntropyTurboController,
                ]
                widget = QComboBox()
                for i in range(len(types)):
                    widget.addItem(
                        types[i].model_fields["name"].default, types[i].model_fields
                    )
                if editor_info is not None:

                    def callback(i):
                        editor_info[0].repopulate_child(
                            editor_info[1],
                            {
                                key: value
                                for key, value in widget.itemData(i).items()
                                if key != "name" and key != "vocs"
                            },
                            {
                                key: value
                                for key, value in widget.itemData(i).items()
                                if key == "name"
                            },
                        )

                    widget.currentIndexChanged.connect(callback)
                    callback(0)
            elif issubclass(resolved_type.main, NumericalOptimizer):
                # hack: replace this?
                types = [LBFGSOptimizer, GridOptimizer]
                widget = QComboBox()
                for i in range(len(types)):
                    widget.addItem(
                        types[i].model_fields["name"].default, types[i].model_fields
                    )
                if editor_info is not None:

                    def callback(i):
                        editor_info[0].repopulate_child(
                            editor_info[1],
                            {
                                key: value
                                for key, value in widget.itemData(i).items()
                                if key != "name"
                            },
                            {
                                key: value
                                for key, value in widget.itemData(i).items()
                                if key == "name"
                            },
                        )

                    widget.currentIndexChanged.connect(callback)
                    callback(0)
            else:
                return None

            if resolved_type.nullable:
                widget.addItem("null", {})

            if default is None:
                default = {"name": "null"}
            if (index := widget.findText(default["name"])) >= 0:
                widget.setCurrentIndex(index)

            if editor_info is not None:
                widget.currentIndexChanged.connect(lambda: editor_info[0].validate())
        elif resolved_type.main == NoneType:
            widget = QLabel()
            widget.setText("null")
        elif resolved_type.main is dict:
            widget = BadgerListEditor(
                resolved_type.subtype[0].main, resolved_type.subtype[1].main
            )

            if default is not None and isinstance(default, dict):
                for k, v in default.items():
                    row = widget.add_widget()
                    _set_value_for_basic_widget(row.parameter1(), k)
                    _set_value_for_basic_widget(row.parameter2(), v)

            if editor_info is not None:
                widget.listChanged.connect(lambda: editor_info[0].validate())
        elif resolved_type.main is list:
            widget = BadgerListEditor(resolved_type.subtype.main)

            if default is not None and isinstance(default, list):
                for v in default:
                    row = widget.add_widget()
                    _set_value_for_basic_widget(row.parameter1(), v)

            if editor_info is not None:
                widget.listChanged.connect(lambda: editor_info[0].validate())
        elif resolved_type.main is float:
            widget = QDoubleSpinBox()
            widget.setRange(float("-inf"), float("inf"))
            widget.setValue(default if default is not None else 0.0)

            if editor_info is not None:
                widget.valueChanged.connect(lambda: editor_info[0].validate())
        elif resolved_type.main is int:
            widget = QSpinBox()
            widget.setRange(-(2**31), 2**31 - 1)  # int32 min/max
            widget.setValue(default if default is not None else 0)

            if editor_info is not None:
                widget.valueChanged.connect(lambda: editor_info[0].validate())
        elif resolved_type.main is bool:
            widget = QCheckBox()
            widget.setChecked(default if default is not None else False)

            if editor_info is not None:
                widget.stateChanged.connect(lambda: editor_info[0].validate())
        else:
            widget = QLineEdit()
            if resolved_type.main == NoneType or default is None:
                widget.setText("null")
            else:
                widget.setText(str(default))

            if editor_info is not None:
                widget.textChanged.connect(lambda: editor_info[0].validate())

        widget.setProperty("badger_nullable", resolved_type.nullable)
        return widget


def _qt_widget_to_yaml_value(widget) -> str:
    if isinstance(widget, QTreeWidget):
        return None
    elif isinstance(widget, BadgerListEditor):
        return widget.get_parameters()
    elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
        return str(widget.value())
    elif isinstance(widget, QCheckBox):
        return "true" if widget.isChecked() else "false"
    elif isinstance(widget, QComboBox):
        if widget.currentText() == "null":
            return "null"
        return f'"{widget.currentText()}"'
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


def _qt_widgets_to_yaml_recurse(table: QTreeWidget, item: QTreeWidgetItem) -> str:
    out = "{"
    for i in range(item.childCount()):
        out += '"' + item.child(i).text(0) + '":'
        widget = table.itemWidget(item.child(i), 1)
        if item.child(i).childCount() > 0:
            out += _qt_widgets_to_yaml_recurse(table, item.child(i))
        elif widget is None:
            out += "null"
        else:
            out += _qt_widget_to_yaml_value(widget)

        if i < item.childCount() - 1:
            out += ","

    out += "}"
    return out


class BadgerListItem(QWidget):
    def __init__(self, editor: "BadgerListEditor", parent=None):
        super().__init__(parent)
        self.editor = editor
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.parameter_value = BadgerResolvedType.resolve_qt(
            editor.widget_type, default=None
        )
        layout.addWidget(self.parameter_value)
        self.parameter_value2 = None
        if editor.widget_type2 is not None:
            self.parameter_value2 = BadgerResolvedType.resolve_qt(
                editor.widget_type2, default=None
            )
            layout.addWidget(self.parameter_value2)
        remove_button = QPushButton("Remove")
        remove_button.setFixedWidth(85)
        remove_button.clicked.connect(self.remove)
        layout.addWidget(remove_button, Qt.AlignRight)

    def parameter1(self):
        return self.parameter_value

    def parameter2(self):
        return self.parameter_value2

    def remove(self):
        self.setParent(None)
        self.deleteLater()
        self.editor.listChanged.emit()


class BadgerListEditor(QWidget):
    listChanged = pyqtSignal()

    def __init__(self, widget_type, widget_type2=None, parent=None):
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
        self.list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)

        add_button = QPushButton("Add")
        add_button.setFixedWidth(90)
        add_button.clicked.connect(self.add_widget)
        layout.addWidget(add_button)

    def add_widget(self):
        widget = BadgerListItem(self)
        self.list_layout.addWidget(widget)
        self.listChanged.emit()
        return widget

    def get_parameters(self):
        child_values = [
            _qt_widget_to_yaml_value(child.parameter_value)
            for child in self.list_container.children()
            if isinstance(child, BadgerListItem)
        ]
        if len(child_values) == 0 and self.property("badger_nullable"):
            return "null"

        if self.widget_type2 is None:
            return "[" + ",".join(child_values) + "]"
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


class BadgerPydanticEditor(QTreeWidget):
    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)
        self.setColumnCount(2)
        self.setColumnWidth(0, 200)
        self.setHeaderLabels(["Parameter", "Value"])

        self.model_class = None

    def _set_params_recurse(
        self,
        parent: Optional[QTreeWidgetItem],
        fields: dict[str, FieldInfo],
        defaults: dict[str, Any] | None,
        hidden,
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
                default=field_info.default
                if defaults is None
                or not isinstance(defaults, dict)
                or defaults[field_name] is None
                or field_name not in defaults
                else defaults[field_name],
                editor_info=(self, child),
            )
            if widget is None:
                resolved = BadgerResolvedType.resolve(field_info.annotation)
                self._set_params_recurse(
                    child,
                    resolved.main.model_fields,
                    None
                    if defaults is None or not isinstance(defaults, dict)
                    else defaults[field_name],
                    hidden,
                )
            else:
                self.setItemWidget(child, 1, widget)

            child.setHidden(hidden)

    def repopulate_child(
        self, child: QTreeWidgetItem, model_fields, model_fields_hidden
    ) -> None:
        for cc in child.takeChildren():
            del cc
        self._set_params_recurse(child, model_fields, None, False)
        self._set_params_recurse(child, model_fields_hidden, None, True)
        child.setExpanded(True)

    def set_params_from_class(self, pydantic_class):
        self.clear()
        self.model_class = pydantic_class
        self._set_params_recurse(None, self.model_class.model_fields, None, False)
        self.validate()

    def set_params_from_generator(self, generator_name, defaults: dict[str, Any]):
        self.clear()
        self.model_class = get_generator(generator_name)
        self._set_params_recurse(
            None,
            {k: v for k, v in self.model_class.model_fields.items() if k in defaults},
            defaults,
            False,
        )
        self.validate()

    def get_parameters(self) -> str:
        return _qt_widgets_to_yaml_recurse(self, self.invisibleRootItem())

    def find_widget_at_path(self, path: list[str]) -> QWidget | None:
        if len(path) == 0:
            return None

        current_items = []
        for i in range(self.topLevelItemCount()):
            current_items.append(self.topLevelItem(i))

        for level, target_name in enumerate(path):
            found_item: QTreeWidgetItem | None = None
            for item in current_items:
                if item.text(0) == target_name:
                    found_item = item
                    break

            if found_item is None:
                return None

            if level == len(path) - 1:
                return self.itemWidget(found_item, 1)

            current_items = []
            for i in range(found_item.childCount()):
                current_items.append(found_item.child(i))

        return None

    def validate(self):
        if self.model_class is None:
            return False

        # Have to reset border styling in case some errors were fixed
        def remove_style(item):
            if item is None:
                return
            self.itemWidget(item, 1).setStyleSheet("")
            for j in range(item.childCount()):
                remove_style(item.child(j))

        self.setStyleSheet("")
        for i in range(self.topLevelItemCount()):
            remove_style(self.topLevelItem(i))

        try:
            parameters = self.get_parameters()

            # hack to pass validation for certain generators
            if issubclass(self.model_class, Generator) and "vocs" not in parameters:
                parameters = (
                    parameters[:-1] + "," * (len(parameters) > 2) + '"vocs":{}}'
                )

            self.model_class.model_validate(yaml.safe_load(parameters))
            return True
        except KeyError as e:
            print(e)
        except ValidationError as e:
            print(e)

            # hack for generators
            if str(e) == "'vocs'" or (
                "turbo_controller.vocs" in str(e) and len(e.errors()) == 1
            ):
                return True

            for error in e.errors():
                if len(error["loc"]) > 0:
                    error_widget = self.find_widget_at_path(error["loc"])
                else:
                    error_widget = self
                if error_widget:
                    error_widget.setStyleSheet(
                        f"{error_widget.metaObject().className()} {{ border: 2px dashed red; }}"
                    )

            return False

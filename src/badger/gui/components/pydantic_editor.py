from dataclasses import dataclass
from types import NoneType
from typing import (
    Annotated,
    Callable,
    Optional,
    Any,
    Sequence,
    TypeVar,
    cast,
    get_origin,
    Union,
    get_args,
)
from inspect import isclass

from pydantic_core import PydanticUndefined
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
    QSizePolicy,
)
from pydantic import BaseModel, Field, ValidationError, create_model
from pydantic.fields import FieldInfo
from xopt.generators import get_generator
from xopt.generators.bayesian.turbo import TurboController
from xopt.numerical_optimizer import NumericalOptimizer
from xopt.generators.bayesian.bayesian_generator import BayesianGenerator

import re
import ast

import logging

from xopt.vocs import VOCS

logger = logging.getLogger(__name__)


T = TypeVar("T")

# Regex to match a tuple string, e.g., "(0.0, 1.0)"
TUPLE_PATTERN = re.compile(r"\((.*?,.*?)\)")


class CustomSafeLoader(yaml.SafeLoader):
    def tuple_constructor(self, node: yaml.ScalarNode | yaml.MappingNode):
        value = self.construct_scalar(node)
        if TUPLE_PATTERN.match(value):
            try:
                return ast.literal_eval(value)
            except Exception:
                pass
        return value


CustomSafeLoader.add_constructor(
    "tag:yaml.org,2002:str", CustomSafeLoader.tuple_constructor
)


def convert_to_type(value: Any, type: Callable[[Any], T]) -> T:
    try:
        return type(value)
    except ValueError:
        raise ValueError(f"Cannot convert {value} to {type}")
    except TypeError:
        raise TypeError(f"Cannot convert {value} to {type}")


def _set_value_for_basic_widget(
    widget: Any,
    value: str | float | int | bool | None,
):
    if isinstance(widget, QLabel) or isinstance(widget, QLineEdit):
        widget.setText("null" if value is None else str(value))
    elif isinstance(widget, QDoubleSpinBox):
        widget.setValue(convert_to_type(value, float))
    elif isinstance(widget, QSpinBox):
        widget.setValue(convert_to_type(value, int))
    elif isinstance(widget, QCheckBox):
        widget.setChecked(convert_to_type(value, bool))


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
            if not isclass(r.main):
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

        if origin == Annotated:
            return BadgerResolvedType.resolve(args[0])

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
        default: float | int | bool | dict[str, Any] | list[Any] | None = None,
        editor_info: tuple["BadgerPydanticEditor", QTreeWidgetItem] | None = None,
    ) -> QWidget | None:
        resolved_type = BadgerResolvedType.resolve(annotation)
        widget = QLabel()

        if resolved_type.main is None:
            widget = QLineEdit()
            widget.setText("null")
        elif issubclass(resolved_type.main, BaseModel):
            if issubclass(resolved_type.main, TurboController):
                widget = QComboBox()
            elif issubclass(resolved_type.main, NumericalOptimizer):
                widget = QComboBox()
            else:
                return None
            if resolved_type.nullable:
                widget.addItem("null", {})

            if default is None:
                default = {"name": "null"}
            if isinstance(default, dict) and "name" in default:
                if (index := widget.findText(default["name"])) >= 0:
                    widget.setCurrentIndex(index)
        elif resolved_type.main == NoneType:
            widget = QLabel()
            widget.setText("null")
        elif resolved_type.main is dict:
            subtypes = resolved_type.subtype
            if subtypes is None:
                raise ValueError("Dict type must have subtypes")
            if not isinstance(subtypes, list) or len(subtypes) != 2:
                raise ValueError("Dict type must have two subtypes")

            primary_type = subtypes[0]
            secondary_type = subtypes[1]

            if primary_type.main is None or secondary_type.main is None:
                raise ValueError("Dict subtypes must be basic types")

            widget = BadgerListEditor(primary_type.main, secondary_type.main)

            if default is not None and isinstance(default, dict):
                for k, v in default.items():
                    row = widget.add_widget()
                    _set_value_for_basic_widget(row.parameter1(), k)
                    _set_value_for_basic_widget(row.parameter2(), v)

            if editor_info is not None:
                widget.listChanged.connect(lambda: handle_changed(editor_info))
        elif resolved_type.main is list:
            if resolved_type.subtype is None:
                raise ValueError("List type must have a subtype")
            if isinstance(resolved_type.subtype, list):
                primary_type = resolved_type.subtype[0]
                secondary_type = (
                    resolved_type.subtype[1] if len(resolved_type.subtype) > 1 else None
                )

            else:
                primary_type = resolved_type.subtype
                secondary_type = None
            if primary_type.main is None:
                raise ValueError("List subtype must be a basic type")
            widget = BadgerListEditor(
                primary_type.main, secondary_type.main if secondary_type else None
            )

            if default is not None and isinstance(default, list):
                for v in default:
                    row = widget.add_widget()
                    _set_value_for_basic_widget(row.parameter1(), v)

            if editor_info is not None:
                widget.listChanged.connect(lambda: handle_changed(editor_info))
        elif resolved_type.main is float:
            widget = QDoubleSpinBox()
            widget.setRange(float("-inf"), float("inf"))
            widget.setDecimals(6)
            value = convert_to_type(default, float) if default is not None else 0.0
            widget.setValue(value)

            if editor_info is not None:
                widget.valueChanged.connect(lambda: handle_changed(editor_info))
        elif resolved_type.main is int:
            widget = QSpinBox()
            widget.setRange(-(2**31), 2**31 - 1)  # int32 min/max
            value = convert_to_type(default, int) if default is not None else 0
            widget.setValue(value)

            if editor_info is not None:
                widget.valueChanged.connect(lambda: handle_changed(editor_info))
        elif resolved_type.main is bool:
            widget = QCheckBox()
            value = convert_to_type(default, bool) if default is not None else False
            widget.setChecked(value)

            if editor_info is not None:
                widget.stateChanged.connect(lambda: handle_changed(editor_info))
        else:
            widget = QLineEdit()
            if default is None:
                widget.setText("null")
            else:
                widget.setText(str(default))

            if editor_info is not None:
                widget.textChanged.connect(lambda: handle_changed(editor_info))

        widget.setProperty("badger_nullable", resolved_type.nullable)
        return widget


def handle_changed(editor_info: tuple["BadgerPydanticEditor", QTreeWidgetItem]):
    tree_widget, _ = editor_info
    tree_widget.validate()


def _qt_widget_to_yaml_value(widget: Any) -> str | None:
    if isinstance(widget, QTreeWidget):
        return None
    elif isinstance(widget, BadgerListEditor):
        return widget.get_parameters_yaml()
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
            return '"null"'
        else:
            return (
                ('"' + widget.text() + '"')
                if isinstance(widget, QLineEdit)
                else widget.text()
            )
    return "null"


def _qt_widgets_to_yaml_recurse(
    table: QTreeWidget,
    item: QTreeWidgetItem | None,
    value_col: int = 1,
) -> str:
    out: str = "{"
    if item is not None:
        for i in range(item.childCount()):
            child_item = item.child(i)
            if child_item is None:
                continue

            child_item_text = child_item.text(0)
            out += f'"{child_item_text}":'
            widget = table.itemWidget(child_item, value_col)

            if child_item.childCount() > 0:
                out += _qt_widgets_to_yaml_recurse(table, child_item)
            elif widget is None:
                out += "null"
            else:
                yaml_value = _qt_widget_to_yaml_value(widget)
                if yaml_value is None:
                    out += "null"
                else:
                    out += yaml_value

            if i < item.childCount() - 1:
                out += ","

    out += "}"
    return out


def _qt_widget_to_value(widget: Any) -> Any:
    if isinstance(widget, QTreeWidget):
        return None
    elif isinstance(widget, BadgerListEditor):
        return widget.get_parameters_dict()
    elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
        return widget.value()
    elif isinstance(widget, QCheckBox):
        return widget.isChecked()
    elif isinstance(widget, QComboBox):
        return widget.currentText()
    elif isinstance(widget, (QLabel, QLineEdit)):
        return widget.text()
    return None


def _qt_widgets_to_values_recurse(
    table: QTreeWidget,
    item: QTreeWidgetItem | None,
    value_col: int = 1,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if item is not None:
        for i in range(item.childCount()):
            child_item = item.child(i)
            if child_item is None:
                continue

            key = child_item.text(0)
            widget = table.itemWidget(child_item, value_col)

            if child_item.childCount() > 0:
                out[key] = _qt_widgets_to_values_recurse(table, child_item)
            elif widget is None:
                out[key] = None
            else:
                out[key] = _qt_widget_to_value(widget)

    return out


class BadgerListItem(QWidget):
    def __init__(self, editor: "BadgerListEditor", parent: QWidget | None = None):
        super().__init__(parent)
        self.editor = editor
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.parameter_value = BadgerResolvedType.resolve_qt(
            editor.widget_type, default=None
        )
        if self.parameter_value:
            self.parameter_value.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            if isinstance(self.parameter_value, QLineEdit):
                self.parameter_value = cast(QLineEdit, self.parameter_value)
                self.parameter_value.editingFinished.connect(
                    lambda: self.editor.listChanged.emit()
                )

        layout.addWidget(self.parameter_value)
        self.parameter_value2 = None
        if editor.widget_type2 is not None:
            self.parameter_value2 = BadgerResolvedType.resolve_qt(
                editor.widget_type2, default=None
            )
            if self.parameter_value2:
                self.parameter_value2.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
                )

                if isinstance(self.parameter_value2, QDoubleSpinBox):
                    self.parameter_value2 = cast(QDoubleSpinBox, self.parameter_value2)
                    self.parameter_value2.valueChanged.connect(
                        lambda: self.editor.listChanged.emit()
                    )
            # Set fixed width for QLineEdit to avoid excessive stretching for dictionary keys
            if isinstance(self.parameter_value, QLineEdit):
                self.parameter_value.setFixedWidth(100)

            layout.addWidget(self.parameter_value2, 1)
        remove_button = QPushButton("Remove")
        remove_button.setFixedWidth(85)
        remove_button.clicked.connect(self.remove)
        layout.addWidget(remove_button, alignment=Qt.AlignmentFlag.AlignRight)

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

        button_layout = QHBoxLayout()

        add_button = QPushButton("Add")
        add_button.setFixedWidth(90)
        add_button.clicked.connect(lambda: self.handle_button_click())
        button_layout.addWidget(add_button)

        layout.addLayout(button_layout)

    def handle_button_click(self):
        self.add_widget()

    def add_widget(self):
        widget = BadgerListItem(self)
        self.list_layout.addWidget(widget)
        self.listChanged.emit()
        return widget

    def get_parameters_yaml(self):
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

    def get_parameters_dict(self):
        child_values: list[str | None] = [
            _qt_widget_to_value(child.parameter_value)
            for child in self.list_container.children()
            if isinstance(child, BadgerListItem)
        ]
        if len(child_values) == 0 and self.property("badger_nullable"):
            return None

        if self.widget_type2 is None:
            return [value for value in child_values if value is not None]
        else:
            child_values2 = [
                _qt_widget_to_value(child.parameter_value2)
                for child in self.list_container.children()
                if isinstance(child, BadgerListItem)
            ]
            return {k: v for k, v in zip(child_values, child_values2)}


class BadgerPydanticEditor(QTreeWidget):
    vocs: VOCS = VOCS()
    defaults: dict[str, Any] = {}
    generator_name: str = ""
    model_class: type[BaseModel] | None = None

    def __init__(
        self,
        parent: QTreeWidget | None = None,
        value_col: int = 1,
        update_callback: Callable[["BadgerPydanticEditor"], None] | None = None,
    ):
        QTreeWidget.__init__(self, parent)
        if value_col < 1:
            value_col = 1
        self.value_col = value_col
        self.update_callback = update_callback
        self.setColumnCount(self.value_col + 1)
        self.setColumnWidth(0, 200)
        self.setHeaderLabels(
            [
                "Parameter" if i == 0 else "Value" if i == self.value_col else ""
                for i in range(0, self.value_col + 1)
            ]
        )

        self.model_class = None

    def _set_params_recurse(
        self,
        parent: Optional[QTreeWidgetItem],
        fields: dict[str, FieldInfo],
        defaults: dict[str, Any] | None,
        hidden: bool,
    ):
        for field_name, field_info in fields.items():
            child = QTreeWidgetItem(
                [field_name if i == 0 else "" for i in range(0, self.value_col + 1)]
            )

            if parent is None:
                self.addTopLevelItem(child)
            else:
                parent.addChild(child)
            child.setToolTip(0, field_info.description)

            widget = BadgerResolvedType.resolve_qt(
                annotation=field_info.annotation,
                default=(
                    field_info.default
                    if defaults is None
                    or field_name not in defaults
                    or defaults[field_name] is None
                    else defaults[field_name]
                ),
                editor_info=(self, child),
            )
            if widget is None:
                resolved = BadgerResolvedType.resolve(field_info.annotation)
                if resolved.main is None or not issubclass(resolved.main, BaseModel):
                    raise ValueError(
                        f"Could not resolve type for field {field_name} with annotation {field_info.annotation}"
                    )
                self._set_params_recurse(
                    child,
                    resolved.main.model_fields,
                    (
                        None
                        if defaults is None
                        or field_name not in defaults
                        or defaults[field_name] is None
                        else defaults[field_name]
                    ),
                    hidden,
                )
            else:
                self.setItemWidget(child, self.value_col, widget)

            child.setDisabled(hidden)
            if widget is not None:
                widget.setDisabled(hidden)

    def initialize_combo_widget(
        self,
        widget: QComboBox,
        selections: Sequence[type[BaseModel] | None],
    ):
        # Clear out existing children
        widget.clear()
        for selection in selections:
            if selection is None:
                widget.addItem("null", selection)
            else:
                widget.addItem(selection.model_fields["name"].default, selection)

    def set_params_from_class(self, pydantic_class: type[Any]):
        self.clear()
        self.model_class = pydantic_class
        self._set_params_recurse(None, self.model_class.model_fields, None, False)
        self.set_params_post_setup({})
        self.validate()

    def set_params_from_dict(self, params: dict[str, Any]):
        self.clear()
        field_definitions: dict[str, tuple[type, FieldInfo]] = {
            k: (type(v), Field()) for k, v in params.items()
        }  # type: ignore
        if field_definitions == {}:
            logger.warning("No fields found in params dictionary")
            return
        self.model_class = cast(
            type[BaseModel],
            create_model("DynamicModel", **field_definitions),  # type: ignore
        )
        self._set_params_recurse(None, self.model_class.model_fields, params, False)

        self.set_params_post_setup(params)
        self.validate()

    def set_params_from_generator(
        self,
        generator_name: str,
        defaults: dict[str, Any],
        vocs: VOCS | None = None,
        validate: bool = True,
    ):
        logger.debug(f"vocs: {vocs}")
        logger.debug(f"defaults: {defaults}")
        self.vocs = vocs or VOCS()
        self.generator_name = generator_name
        self.defaults = defaults

        self.clear()
        self.model_class = get_generator(generator_name)

        defaults["vocs"] = self.vocs.model_dump()

        fields_to_remove = ["vocs"]

        filtered_class_fields, removed_class_fields = self.filter_class_fields(
            self.model_class, fields_to_remove, defaults, include_defaults=True
        )

        self._set_params_recurse(
            None,
            filtered_class_fields,
            defaults,
            False,
        )

        self._set_params_recurse(
            None,
            removed_class_fields,
            defaults,
            True,
        )

        # Update parameters with defaults from generator class
        self.set_params_post_setup(defaults)

        if validate:
            self.validate()

    def set_params_post_setup(self, defaults: dict[str, Any]):
        if self.model_class is None:
            raise ValueError("Model class is not set.")

        if issubclass(self.model_class, BayesianGenerator):
            if self.model_class.model_fields.get("turbo_controller") is not None:
                self.initialize_special_field(defaults, "turbo_controller")

            if self.model_class.model_fields.get("numerical_optimizer") is not None:
                self.initialize_special_field(defaults, "numerical_optimizer")

    def initialize_special_field(self, defaults: dict[str, Any], field: str):
        widget_items = self.findItems(field, Qt.MatchFlag.MatchExactly)

        if len(widget_items) == 0:
            logger.warning(
                f"Generator has {field} set but no compatible {field} item exists in tree. Item has likely been filtered out from not being included in defaults when setting parameters."
            )
            return

        special_item = widget_items[0]

        # Initialize combo box for special item
        widget = self.itemWidget(special_item, self.value_col)
        if widget is None or not isinstance(widget, QComboBox):
            raise ValueError(f"{field} does not have a combo box widget.")
        widget = cast(QComboBox, widget)

        selections = self.get_all_compatible_classes(field)

        self.initialize_combo_widget(widget, selections)

        special_item_dict: dict[str, Any] | None = defaults.get(field, {})

        if special_item_dict is None:
            logger.warning(
                f"Generator has {field} set but no compatible {field} exists."
            )
            special_item_dict = {}

        special_item_dict["vocs"] = self.vocs.model_dump()

        name = special_item_dict.get("name", "")

        # Update combo box selection with name
        if (index := widget.findText(name) if name else widget.findText("null")) >= 0:
            widget.setCurrentIndex(index)

        self.update_params_from_generator_class(
            special_item,
            name,
            field,
            special_item_dict,
        )

        widget.currentIndexChanged.connect(
            lambda: self.on_radio_changed(special_item, "turbo_controller")
        )

    def get_all_compatible_classes(self, field_name: str):
        if self.model_class is None:
            raise ValueError("Model class is not set.")

        compatible_classes: Sequence[type[BaseModel] | None] = []

        if field_name == "numerical_optimizer":
            if not issubclass(self.model_class, BayesianGenerator):
                raise ValueError("Generator does not support numerical optimizers.")
            compatible_classes = self.model_class.get_compatible_numerical_optimizers()
        elif field_name == "turbo_controller":
            if not issubclass(self.model_class, BayesianGenerator):
                raise ValueError("Generator does not support turbo controllers.")
            compatible_classes = self.model_class.get_compatible_turbo_controllers()
        else:
            raise ValueError(f"Field name {field_name} is not recognized.")

        return compatible_classes

    def get_compatible_class(self, name: str, field_name: str) -> type[BaseModel]:
        compatible_classes = self.get_all_compatible_classes(field_name)

        selected_class: type[BaseModel] | None = None

        for opt in compatible_classes:
            if opt is None:
                if name == "null":
                    break
            else:
                if opt.model_fields["name"].default == name:
                    selected_class = opt
                    break

        if selected_class is None:
            raise ValueError(
                f"Generator has numerical optimizer set but no compatible numerical optimizer with name {name} exists."
            )

        return selected_class

    def on_radio_changed(
        self,
        tree_widget_item: QTreeWidgetItem,
        field_name: str,
    ):
        # Clear out existing children
        for cc in tree_widget_item.takeChildren():
            del cc

        widget = self.itemWidget(tree_widget_item, self.value_col)
        if widget is None or not isinstance(widget, QComboBox):
            raise ValueError("tree widget item does not have a combo box widget.")
        widget = cast(QComboBox, widget)

        name = widget.currentText()
        if name == "null":
            return

        # get values from current parameters
        parameters = self.get_parameters_yaml()
        defaults = yaml.load(parameters, Loader=CustomSafeLoader)
        self.update_params_from_generator_class(
            tree_widget_item,
            name,
            field_name,
            defaults,
        )

        self.validate()

    def update_params_from_generator_class(
        self,
        tree_widget_item: QTreeWidgetItem,
        name: str,
        field_name: str,
        defaults: dict[str, Any],
    ):
        try:
            pydantic_class = self.get_compatible_class(name, field_name)
        except ValueError:
            logger.warning(
                f"Could not find compatible class for {name} in field {field_name}"
            )
            return

        fields_to_remove = ["name", "vocs"]

        filtered_class_fields, removed_class_fields = self.filter_class_fields(
            pydantic_class, fields_to_remove, include_defaults=False
        )

        self._set_params_recurse(
            tree_widget_item,
            filtered_class_fields,
            defaults,
            False,
        )
        self._set_params_recurse(
            tree_widget_item,
            removed_class_fields,
            defaults,
            True,
        )

        self.expandItem(tree_widget_item)

    @staticmethod
    def filter_class_fields(
        pydantic_class: type[BaseModel],
        fields_to_remove: list[str] = [],
        defaults: dict[str, Any] = {},
        include_defaults: bool = False,
    ) -> tuple[dict[str, FieldInfo], dict[str, FieldInfo]]:
        condition: Callable[[str], bool]

        def include_condition(k: str) -> bool:
            return k in defaults and k not in fields_to_remove

        def exclude_condition(k: str) -> bool:
            return k not in fields_to_remove

        if include_defaults:
            condition = include_condition
        else:
            condition = exclude_condition

        filtered_class_fields = {
            k: v for k, v in pydantic_class.model_fields.items() if condition(k)
        }

        removed_class_fields = {
            k: v
            for k, v in pydantic_class.model_fields.items()
            if k in fields_to_remove
        }

        return filtered_class_fields, removed_class_fields

    @staticmethod
    def get_defaults_from_type(pydantic_class: type[Any]):
        if not issubclass(pydantic_class, BaseModel):
            raise ValueError("Provided class is not a Pydantic model")
        defaults: dict[str, Any] = {}
        for field_name, field_info in pydantic_class.model_fields.items():
            if field_info.default is not PydanticUndefined:
                defaults[field_name] = field_info.default
            elif field_info.default_factory is not None:
                defaults[field_name] = field_info.default_factory()  # type: ignore
        return defaults

    def get_parameters_yaml(self) -> str:
        return _qt_widgets_to_yaml_recurse(
            self, self.invisibleRootItem(), self.value_col
        )

    def get_parameters_dict(self) -> dict[str, Any]:
        return _qt_widgets_to_values_recurse(
            self, self.invisibleRootItem(), self.value_col
        )

    def find_widget_at_path(
        self, path: tuple[int | str, ...]
    ) -> QTreeWidgetItem | None:
        if len(path) == 0:
            return None

        current_items: list[QTreeWidgetItem | None] = []
        for i in range(self.topLevelItemCount()):
            current_items.append(self.topLevelItem(i))

        for level, target_name in enumerate(path):
            found_item: QTreeWidgetItem | None = None
            for item in current_items:
                if item is None:
                    continue
                if item.text(0) == target_name:
                    found_item = item
                    break

            if found_item is None:
                return None

            if level == len(path) - 1:
                return found_item

            current_items = []
            for i in range(found_item.childCount()):
                current_items.append(found_item.child(i))

        return None

    def remove_style(self, item: QTreeWidgetItem | None):
        # Have to reset border styling in case some errors were fixed
        if item is None:
            return
        item.setData(0, Qt.ItemDataRole.BackgroundRole, None)
        item.setToolTip(0, "")
        widget = self.itemWidget(item, self.value_col)
        if widget:
            widget.setStyleSheet("")
        for j in range(item.childCount()):
            self.remove_style(item.child(j))

    def update_vocs(self, vocs: VOCS):
        logger.debug(f"Updating VOCS in BadgerPydanticEditor: {vocs}")
        self.vocs = vocs

        parameters = self.get_parameters_yaml()
        logger.debug(f"Extracted parameters from tree: {parameters}")

        defaults = yaml.load(parameters, Loader=CustomSafeLoader)

        self.set_params_from_generator(self.generator_name, defaults, self.vocs)
        self.validate()

    def update_after_validate(self, defaults: dict[str, Any]):
        model_class = self.model_class
        if model_class is None:
            return

        self.clear()

        fields_to_remove = ["vocs"]

        filtered_class_fields, removed_class_fields = self.filter_class_fields(
            model_class, fields_to_remove, defaults, include_defaults=True
        )

        self._set_params_recurse(
            None,
            filtered_class_fields,
            defaults,
            False,
        )

        self._set_params_recurse(
            None,
            removed_class_fields,
            defaults,
            True,
        )

        # Update parameters with defaults from generator class
        self.set_params_post_setup(defaults)

        if self.update_callback is not None:
            self.update_callback(self)

    def validate(self):
        if self.model_class is None:
            return False

        self.setStyleSheet("")
        for i in range(self.topLevelItemCount()):
            self.remove_style(self.topLevelItem(i))

        try:
            parameters = self.get_parameters_yaml()

            parameters_dict = yaml.load(parameters, Loader=CustomSafeLoader)

            model = self.model_class.model_validate(parameters_dict)

            # After we validate the model, some fields may have been changed due to any validation logic present within the Pydantic model (i.e. field validators changing default values). We need to update the tree to reflect these changes.
            defaults = model.model_dump()
            defaults = {k: v for k, v in defaults.items() if k in parameters_dict}

            # FIX: `vocs` Field in the Xopt Generator model has an explicit "exclude=True" which prevents the `vocs` field from being serialized when using model_dump(). This field needs to be present to properly validate the model. We have to manually re-add it here.
            defaults["vocs"] = self.vocs.model_dump()

            self.update_after_validate(defaults)

            return True
        except KeyError as e:
            logger.error(e)
        except ValidationError as e:
            logger.error(e)

            for error in e.errors():
                loc = error["loc"]
                msg = error["msg"]
                if len(loc) > 0:
                    error_widget = self.find_widget_at_path(loc)
                else:
                    error_widget = self
                if error_widget:
                    if type(error_widget) is QTreeWidgetItem:
                        error_widget.setBackground(0, Qt.GlobalColor.red)
                        widget = self.itemWidget(error_widget, self.value_col)
                        if widget is not None:
                            widget.setProperty("error", True)
                            widget.setStyleSheet(
                                '*[error="true"] { border: 2px dashed red }'
                            )
                            if isinstance(widget, BadgerListEditor):
                                widget = cast(BadgerListEditor, widget)
                                widget.list_container.setProperty("error", True)
                                widget.list_container.setStyleSheet(
                                    '*[error="true"] { border: 2px dashed red }'
                                )

                        error_widget.setToolTip(0, msg)
                    else:
                        error_widget = cast(QTreeWidget, error_widget)
                        error_widget.setProperty("error", True)
                        error_widget.setStyleSheet(
                            '*[error="true"] { border: 2px dashed red }'
                        )
                        error_widget.setToolTip(msg)
            return False

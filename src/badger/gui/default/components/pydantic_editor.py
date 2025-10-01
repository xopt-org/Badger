from dataclasses import dataclass
from types import NoneType
from typing import (
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
)
from pydantic import BaseModel, Field, ValidationError, create_model
from pydantic.fields import FieldInfo
from xopt.generator import Generator
from xopt.generators import get_generator
from xopt.generators.bayesian.turbo import TurboController
from xopt.numerical_optimizer import NumericalOptimizer
from xopt.generators.bayesian.bayesian_generator import BayesianGenerator

import logging

from xopt.vocs import VOCS

logger = logging.getLogger(__name__)


T = TypeVar("T")


def convert_to_type(value: Any, type: Callable[[Any], T]) -> T:
    try:
        return type(value)
    except ValueError:
        raise ValueError(f"Cannot convert {value} to {type}")


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
                for controller in TurboController.__subclasses__():
                    widget.addItem(controller.model_fields["name"].default, controller)

            elif issubclass(resolved_type.main, NumericalOptimizer):
                widget = QComboBox()
                for optimizer in NumericalOptimizer.__subclasses__():
                    widget.addItem(optimizer.model_fields["name"].default, optimizer)

            else:
                return None

            if resolved_type.nullable:
                widget.addItem("null", {})

            if default is None:
                default = {"name": "null"}
            if isinstance(default, dict) and "name" in default:
                if (index := widget.findText(default["name"])) >= 0:
                    widget.setCurrentIndex(index)

            # if editor_info is not None:
            #     widget.currentIndexChanged.connect(lambda: handle_changed(editor_info))
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
    editor_info[0].validate()


def _qt_widget_to_yaml_value(widget: Any) -> str | None:
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


def _qt_widgets_to_yaml_recurse(
    table: QTreeWidget, item: QTreeWidgetItem | None
) -> str:
    out: str = "{"
    if item is not None:
        for i in range(item.childCount()):
            child_item = item.child(i)
            if child_item is None:
                continue
            out += f'"{child_item.text(0)}":'
            widget = table.itemWidget(child_item, 1)
            if widget is None:
                out += "null"
            else:
                if child_item.childCount() > 0:
                    out += _qt_widgets_to_yaml_recurse(table, child_item)
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


class BadgerListItem(QWidget):
    def __init__(self, editor: "BadgerListEditor", parent: QWidget | None = None):
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
        layout.addWidget(remove_button, Qt.AlignmentFlag.AlignRight)

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

        add_button = QPushButton("Add")
        add_button.setFixedWidth(90)
        add_button.clicked.connect(lambda: self.handle_button_click())
        layout.addWidget(add_button)

    def handle_button_click(self):
        self.add_widget()

    def add_widget(self):
        widget = BadgerListItem(self)
        self.list_layout.addWidget(widget)
        self.listChanged.emit()
        return widget

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


class BadgerPydanticEditor(QTreeWidget):
    vocs: VOCS | None = None
    model_class: type[BaseModel] | None = None

    def __init__(
        self,
        parent: QTreeWidget | None = None,
    ):
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
        hidden: bool,
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
                default=(
                    field_info.default
                    if defaults is None
                    # or not isinstance(defaults, dict)
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
                    (None if defaults is None else defaults[field_name]),
                    hidden,
                )
            else:
                self.setItemWidget(child, 1, widget)

            child.setHidden(hidden)

    def handle_repopulate(
        self,
        widget: QComboBox,
        tree_widget_item: QTreeWidgetItem,
        types: Sequence[type[BaseModel]],
        defaults: dict[str, Any],
    ):
        for i in range(len(types)):
            widget.addItem(types[i].model_fields["name"].default, types[i].model_fields)

        # widget.currentIndexChanged.connect(
        #     lambda: self.on_repopulate_changed(widget, tree_widget_item, defaults)
        # )
        # widget.currentIndexChanged.emit(0)

    def on_repopulate_changed(
        self,
        widget: QComboBox,
        tree_widget_item: QTreeWidgetItem,
        defaults: dict[str, Any],
    ):
        model_fields = {
            key: value
            for key, value in widget.itemData(widget.currentIndex()).items()
            if key in defaults
        }

        hidden_model_fields = {
            key: value
            for key, value in widget.itemData(widget.currentIndex()).items()
            if key == "name"
        }

        self.repopulate_child(
            tree_widget_item,
            model_fields,
            hidden_model_fields,
            defaults,
        )

    def repopulate_child(
        self,
        child: QTreeWidgetItem,
        model_fields: dict[str, FieldInfo],
        model_fields_hidden: dict[str, FieldInfo],
        defaults: dict[str, Any],
    ) -> None:
        for cc in child.takeChildren():
            del cc
        self._set_params_recurse(child, model_fields, defaults, False)
        # self._set_params_recurse(child, model_fields_hidden, defaults, True)
        child.setExpanded(True)

    def set_params_from_class(self, pydantic_class: type[Any]):
        self.clear()
        self.model_class = pydantic_class
        self._set_params_recurse(None, self.model_class.model_fields, None, False)
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
        self.validate()

    def set_params_from_generator(
        self, generator_name: str, defaults: dict[str, Any], vocs: VOCS | None = None
    ):
        logger.debug(f"vocs: {vocs}")
        logger.debug(f"defaults: {defaults}")
        self.vocs = vocs
        self.clear()
        self.model_class = get_generator(generator_name)
        self._set_params_recurse(
            None,
            {k: v for k, v in self.model_class.model_fields.items() if k in defaults},
            defaults,
            False,
        )
        # Update parameters with defaults from generator class
        if issubclass(self.model_class, BayesianGenerator):
            if self.model_class.model_fields.get("turbo_controller") is not None:
                # self.initialize_turbo_controller_field(defaults)
                pass

            if self.model_class.model_fields.get("numerical_optimizer") is not None:
                self.initialize_numerical_optimizer_field(defaults)

        # self.validate()

    def initialize_numerical_optimizer_field(self, defaults: dict[str, Any]):
        numerical_optimizer_items = self.findItems(
            "numerical_optimizer", Qt.MatchFlag.MatchExactly
        )

        if len(numerical_optimizer_items) == 0:
            raise ValueError(
                "Generator has numerical optimizer set but no compatible numerical optimizer item exists in tree. Item has likely been filtered out from not being included in defaults when setting parameters."
            )

        numerical_optimizer_item = numerical_optimizer_items[0]

        num_optimizer_dict = defaults.get("numerical_optimizer", None)

        if num_optimizer_dict is None:
            raise ValueError(
                "Generator has numerical optimizer set but no compatible numerical optimizer exists."
            )

        name = num_optimizer_dict.get("name", None)
        if name is None:
            raise ValueError(
                "Generator has numerical optimizer set but no name exists in the numerical optimizer defaults."
            )

        self.update_params_from_generator_class(
            numerical_optimizer_item,
            name,
            "numerical_optimizer",
            num_optimizer_dict,
        )

        widget = self.itemWidget(numerical_optimizer_item, 1)
        if widget is not None:
            if isinstance(widget, QComboBox):
                widget = cast(QComboBox, widget)

                widget.currentIndexChanged.connect(
                    lambda: self.on_radio_changed(
                        widget,
                        numerical_optimizer_item,
                        "numerical_optimizer",
                        num_optimizer_dict,
                    )
                )

    def initialize_turbo_controller_field(self, defaults: dict[str, Any]):
        turbo_controller_items = self.findItems(
            "turbo_controller", Qt.MatchFlag.MatchExactly
        )

        if len(turbo_controller_items) == 0:
            logger.warning(
                "Generator has turbo controller set but no compatible turbo controller item exists in tree. Item has likely been filtered out from not being included in defaults when setting parameters."
            )
            return

        turbo_controller_item = turbo_controller_items[0]

        turbo_controller_dict = defaults.get("turbo_controller", None)

        if turbo_controller_dict is None:
            logger.warning(
                "Generator has turbo controller set but no compatible turbo controller exists."
            )
            return

        widget = self.itemWidget(turbo_controller_item, 1)
        if widget is not None:
            if isinstance(widget, QComboBox):
                widget = cast(QComboBox, widget)

                widget.currentIndexChanged.connect(
                    lambda: self.on_radio_changed(
                        widget,
                        turbo_controller_item,
                        "turbo_controller",
                        turbo_controller_dict,
                    )
                )

        name = turbo_controller_dict.get("name", None)
        if name is None:
            logger.warning(
                "Generator has turbo controller set but no name exists in the turbo controller defaults."
            )
            return

        self.update_params_from_generator_class(
            turbo_controller_item,
            name,
            "turbo_controller",
            turbo_controller_dict,
        )

    def get_compatible_class(self, name: str, field_name: str) -> type[BaseModel]:
        if self.model_class is None:
            raise ValueError("Model class is not set.")

        compatible_classes: Sequence[type[BaseModel]] = []

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

        numerical_optimizer_class: type[BaseModel] | None = None

        for opt in compatible_classes:
            if opt.model_fields["name"].default == name:
                numerical_optimizer_class = opt
                break

        if numerical_optimizer_class is None:
            raise ValueError(
                f"Generator has numerical optimizer set but no compatible numerical optimizer with name {name} exists."
            )

        return numerical_optimizer_class

    def on_radio_changed(
        self,
        widget: QComboBox,
        tree_widget_item: QTreeWidgetItem,
        field_name: str,
        defaults: dict[str, Any],
    ):
        # Clear out existing children
        for cc in tree_widget_item.takeChildren():
            del cc

        name = widget.currentText()
        if name == "null":
            return

        self.update_params_from_generator_class(
            tree_widget_item,
            name,
            field_name,
            defaults,
        )

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
            # self.remove_style(tree_widget_item)
            return

        filtered_class_fields, removed_class_fields = self.filter_class_fields(
            pydantic_class
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

    def filter_class_fields(
        self, pydantic_class: type[BaseModel]
    ) -> tuple[dict[str, FieldInfo], dict[str, FieldInfo]]:
        fields_to_remove = ["name"]

        filtered_class_fields = {
            k: v
            for k, v in pydantic_class.model_fields.items()
            if k not in fields_to_remove
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

    def get_parameters(self) -> str:
        return _qt_widgets_to_yaml_recurse(self, self.invisibleRootItem())

    def find_widget_at_path(self, path: tuple[int | str, ...]) -> QWidget | None:
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
                return self.itemWidget(found_item, 1)

            current_items = []
            for i in range(found_item.childCount()):
                current_items.append(found_item.child(i))

        return None

    def remove_style(self, item: QTreeWidgetItem | None):
        # Have to reset border styling in case some errors were fixed
        if item is None:
            return
        widget = self.itemWidget(item, 1)
        if widget:
            widget.setStyleSheet("")
        for j in range(item.childCount()):
            self.remove_style(item.child(j))

    def validate(self):
        if self.model_class is None:
            return False

        self.setStyleSheet("")
        for i in range(self.topLevelItemCount()):
            self.remove_style(self.topLevelItem(i))

        try:
            parameters = self.get_parameters()

            # hack to pass validation for certain generators
            if issubclass(self.model_class, Generator) and "vocs" not in parameters:
                if self.vocs is None:
                    vocs = {}
                else:
                    vocs = str(self.vocs.model_dump())

                parameters = (
                    parameters[:-1]
                    + "," * (len(parameters) > 2)
                    + f'"vocs":{vocs}'
                    + "}"
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
                loc = error["loc"]
                if len(loc) > 0:
                    error_widget = self.find_widget_at_path(loc)
                else:
                    error_widget = self
                if error_widget:
                    meta_object = error_widget.metaObject()
                    if meta_object is not None:
                        error_widget.setStyleSheet(
                            f"{meta_object.className()} {{ border: 2px dashed red; }}"
                        )

            return False

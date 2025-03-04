from typing import Generic, TypeVar
from collections.abc import Callable
from openglider.gui.qt import QtWidgets

T = TypeVar("T")

class Input(Generic[T], QtWidgets.QWidget):
    on_change: list[Callable[[T], None]]
    on_changed: list[Callable[[T], None]]

    def __init__(self, parent: QtWidgets.QWidget=None, name: str="", default: T=None, vertical: bool=False):
        super().__init__(parent=parent)
        self.name = name
        
        self.on_change = []
        self.on_changed = []

        if vertical:
            layout: QtWidgets.QVBoxLayout | QtWidgets.QHBoxLayout = QtWidgets.QVBoxLayout()
        else:
            layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)

        label = QtWidgets.QLabel(name)
        layout.addWidget(label)

        self.input = QtWidgets.QLineEdit(parent=self)
        if default is not None:
            self.set_value(default, propagate=True)
        self.input.setObjectName(name)

        layout.addWidget(self.input)

        self.input.textChanged.connect(self._on_change)
        self.input.editingFinished.connect(self._on_changed)
    
    def set_value(self, value: T, propagate: bool=False) -> None:
        self.value = value
        if propagate:
            self.input.setText(str(value))

    def _on_change(self, text: T) -> None:
        self.set_value(text)
        for f in self.on_change:
            f(self.value)

    def _on_changed(self) -> None:
        self.input.setText(str(self.value))
        for f in self.on_changed:
            f(self.value)


class NumberInput(Input[float]):
    on_change: list[Callable[[float], None]]  # type: ignore
    on_changed: list[Callable[[float], None]]  # type: ignore

    def __init__(
        self,
        parent: QtWidgets.QWidget=None,
        name: str="",
        min_value: float | None=None,
        max_value: float | None=None,
        places: int | None=None,
        default: float | None=None,
        vertical: bool=False
        ):

        self.min_value = min_value
        self.max_value = max_value
        self.places = places
        super().__init__(parent, name, default, vertical)  # type: ignore

    def set_value(self, value: float, propagate: bool=False) -> None:  # type: ignore
        value = float(value)
        if self.min_value is not None:
            value = max(self.min_value, value)

        if self.max_value is not None:
            value = min(self.max_value, value)

        if self.places is not None:
            value = round(value, self.places)
        
        super().set_value(value, propagate)  # type: ignore


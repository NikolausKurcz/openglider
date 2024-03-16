from typing import Any
from openglider.gui.qt import QtWidgets, QtCore
import enum

import logging
logger = logging.getLogger(__name__)

class EnumSelection(QtWidgets.QWidget):
    changed = QtCore.Signal()

    def __init__(self, choices: type[enum.Enum], parent: QtWidgets.QWidget=None) -> None:
        super().__init__(parent)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.choices = choices

        self.selector = QtWidgets.QComboBox()
        self.layout().addWidget(self.selector)

        self.choice_list = []

        for x in self.choices:
            self.choice_list.append(x)
            self.selector.addItem(x.name)
            
        
        self.selector.activated.connect(self._update)
        #self.selector.changed.connect(self._update)
    
    @property
    def selected(self) -> enum.Enum:
        return self.choice_list[self.selector.currentIndex()]
    
    def select(self, value: Any) -> None:
        for i, x in enumerate(self.choices):  # type: ignore
            if x == value or x.value == value:
                self.selector.setCurrentIndex(i)
                return
        
        raise ValueError(f"no such option: {value}")
    
    def _update(self, value: int) -> None:
        self.changed.emit()
        
    
class AutoComplete(QtWidgets.QWidget):
    changed = QtCore.Signal()
    choices: list[str]

    def __init__(self, choices: list[str], parent: QtWidgets.QWidget=None) -> None:
        super().__init__(parent)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.choices = choices

        self.selector = QtWidgets.QComboBox()
        self.layout().addWidget(self.selector)

        for x in self.choices:
            self.selector.addItem(x)
            
        
        self.selector.activated.connect(self._update)
        #self.selector.changed.connect(self._update)
    
    def update_choices(self, choices: list[str]) -> None:
        self.selector.clear()
        self.choices = choices
        self.selector.addItems(choices)
    
    @property
    def selected(self) -> str:
        return self.choices[self.selector.currentIndex()]
    
    def select(self, value: str) -> None:
        for i, x in enumerate(self.choices):  # type: ignore
            if x == value:
                self.selector.setCurrentIndex(i)
                return
        
        raise ValueError(f"no such option: {value}")
    
    def _update(self, value: int) -> None:
        self.changed.emit()



from typing import Dict, Tuple, List
import logging

from openglider.gui.qt import QtWidgets

#from openglider.gui.wizzards.abwicklung import PlotWizzard
#from openglider.gui.wizzards.line_forces import LineForceView

logger = logging.getLogger(__name__)
__all__ = ["menu_actions"]

menu_actions: Dict[str, List[Tuple[object, QtWidgets.QWidget]]] = {
    "view": [
        #(PlotWizzard, "Abwicklung"),
        #(LineForceView, "Leinen")
    ]
}

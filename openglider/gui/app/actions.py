import logging


from openglider.gui.wizzards.base import Wizard
from openglider.gui.wizzards.input import input_wizzards
from openglider.gui.wizzards.line_forces import LineForceView

logger = logging.getLogger(__name__)
__all__ = ["menu_actions"]

menu_actions: dict[str, list[tuple[type[Wizard], str]]] = {
    "view": [
        (LineForceView, "Lines")
    ],
    "edit": input_wizzards
}


def add_actions(actions: dict[str, list[tuple[type[Wizard], str]]]) -> None:
    for group_name, group_actions in actions.items():
        menu_actions.setdefault(group_name, [])
        menu_actions[group_name] += group_actions

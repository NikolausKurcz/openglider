from typing import Type
from collections.abc import Callable

from mypy.plugin import ClassDefContext, Plugin
from mypy.plugins import dataclasses


def plugin(version: str) -> 'Type[Plugin]':
    """
    `version` is the mypy version string
    We might want to use this to print a warning if the mypy version being used is
    newer, or especially older, than we expect (or need).
    """
    return OpengliderPlugin


class OpengliderPlugin(Plugin):
    dataclass_fullname: str = "openglider.utils.dataclass.dataclass"
    def get_class_decorator_hook_2(self, fullname: str) -> Callable[[ClassDefContext], bool] | None:
        if fullname == self.dataclass_fullname:
            return dataclasses.dataclass_class_maker_callback
        return None

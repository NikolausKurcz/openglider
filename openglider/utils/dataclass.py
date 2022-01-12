from typing import TYPE_CHECKING
import pydantic
#from pydantic import Field as field
from dataclasses import asdict, replace, field

class Config:
    arbitrary_types_allowed = True

def dataclass(_cls):
    _cls_new = pydantic.dataclasses.dataclass(config=Config)(_cls)

    old_json = getattr(_cls_new, "__json__", None)
    if old_json is None or getattr(old_json, "is_auto", False):
        def __json__(instance):
            return instance.json()
        
        __json__.is_auto = True

        _cls_new.__json__ = __json__

    old_copy = getattr(_cls_new, "copy", None)
    if old_copy is None or getattr(old_copy, "is_auto", False):
        def copy(instance):
            return  replace(instance)
        
        copy.is_auto = True

        _cls_new.copy = copy

    return _cls_new

class BaseModel(pydantic.BaseModel):
    def __json__(self):
        return self.json()
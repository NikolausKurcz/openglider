import logging
import math
import operator
import re
from typing import Any, ClassVar, Self, TypeVar
from collections.abc import Callable

import pydantic

logger = logging.Logger(__name__)
OpReturnType = TypeVar("OpReturnType")

#@dataclass(frozen=True, init=False)
class Quantity(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        frozen=True,
        extra="forbid"
    )
    __pydantic_custom_init__ = True
    value: float

    unit: ClassVar[str]
    unit_variants: ClassVar[dict[str, float]]
    display_unit: str | None = None

    re_number: ClassVar[str] = r"[+-]?(?:(?:\d+\.?\d*)|(?:\.\d+))(?:[eE][+-]?\d+)?|\d+"
    re_unit: ClassVar[str] = r"[\w°%]+)(?!\S"
    re_number_only: ClassVar[re.Pattern] = re.compile(f"^\s*({re_number})\s*$")
    re_combined: ClassVar[re.Pattern] = re.compile(f"({re_number})\s*({re_unit})")

    def __init__(self, value: float | str, unit: str | None=None, display_unit: str | None=None):
        data = self._get_init_args(value, unit, display_unit)
        super().__init__(**data)
    
    @classmethod
    def _get_init_args(cls, value: float | str, unit: str | None=None, display_unit: str | None=None) -> dict[str, Any]:
        value_float = None
        if isinstance(value, str):
            if cls.re_number_only.match(value):
                value_float = float(value)
            else:
                assert unit is None
                if match := cls.re_combined.match(value):
                    value_str, unit = match.groups()
                    value_float = float(value_str)
        
        if value_float is None:
            value_float = float(value)

        factor = 1.

        if unit is not None and unit != cls.unit:
            try:
                factor = cls.unit_variants[unit]
            except KeyError:
                raise ValueError(f"invalid unit for {cls.__name__}: {unit}")
        
        dct: dict[str, Any] = {
            "value": value_float * factor,
        }

        if unit or display_unit:
            dct["display_unit"] = unit or display_unit
        
        return dct

    def get(self, unit: str | None=None) -> float:
        if unit is None or unit == self.unit:
            return self.value
        
        factor = self.unit_variants[unit]
        return self.value / factor
    
    def _get_display_value(self) -> tuple[float, str]:
        if self.display_unit is not None and self.display_unit != self.unit:
            return self.value / self.unit_variants[self.display_unit], self.display_unit
        
        # TODO: return best-fit unit instead
        
        return self.value, self.unit
    
    def __json__(self) -> str:
        return repr(self)
    
    def __repr__(self) -> str:
        value, unit = self._get_display_value()

        return f"{value}{unit}"
        
    def __format__(self, spec: str) -> str:
        value, unit = self._get_display_value()
        return f"{value.__format__(spec)}{unit}"
    
    def __hash__(self) -> int:
        return hash(self.value)
    
    def __apply_operator(self, other: Any, operator: Callable[[float, float], float]) -> Self:
        new_value: float | None = None
        display_unit: str | None = None

        if isinstance(other, self.__class__):
            new_value = operator(self.value, other.value)
            if other.display_unit is None or self.display_unit == other.display_unit:
                display_unit = self.display_unit
        elif isinstance(other, (float, int)):
            new_value = operator(self.value, other)
            display_unit = self.display_unit
        else:
            raise ValueError(f"cannot do '{operator}' with {self.unit} and {type(other)}")
        
        return self.__class__(
            value=new_value,
            display_unit=display_unit
        )
    
    def __str__(self) -> str:
        value, unit = self._get_display_value()
        return f"{value}{unit}"
    
    def __apply_cmp(self, other: Any, operator: Callable[[float, float], OpReturnType]) -> OpReturnType:
        if isinstance(other, self.__class__):
            return operator(self.value, other.value)
        elif isinstance(other, (float, int)):
            return operator(self.value, other)
        else:
            raise ValueError(f"")
        
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.value == other.value
        elif isinstance(other, Quantity):
            return False
        
        return self.value == other
    
    def __add__(self, other: Any) -> Self:
        return self.__apply_operator(other, operator.add)
    
    def __sub__(self, other: Any) -> Self:
        return self.__apply_operator(other, operator.sub)
    
    def __mul__(self, other: Any) -> Self:
        return self.__apply_operator(other, operator.mul)
    
    def __rmul__(self, other: Any) -> Self:
        return self.__apply_operator(other, operator.mul)
    
    def __truediv__(self, other: Any) -> Self:
        return self.__apply_operator(other, operator.truediv)
    
    def __neg__(self) -> Self:
        return self.__apply_operator(-1, operator.mul)
    
    def __gt__(self, other: Any) -> bool:
        return self.__apply_cmp(other, operator.gt)
    
    def __ge__(self, other: Any) -> bool:
        return self.__apply_cmp(other, operator.ge)
    
    def __lt__(self, other: Any) -> bool:
        return self.__apply_cmp(other, operator.lt)
    
    def __le__(self, other: Any) -> bool:
        return self.__apply_cmp(other, operator.le)
    
    def __float__(self) -> float:
        return self.value
    
    def __abs__(self) -> float:
        return self.value.__abs__()
    
    @property
    def si(self) -> float:
        return self.value
    
    @pydantic.model_validator(mode="before")
    @classmethod
    def _validate(cls, v: Any) -> dict[str, Any] | Self:
        if isinstance(v, (str, float, int)):
            return cls._get_init_args(value=v)
        elif isinstance(v, cls):
            if v.unit == cls.unit:
                return v
        elif isinstance(v, dict):
            return v

        raise ValueError(f"Invalid value for {cls}: {v}")
    
    @classmethod
    def get_regex(cls) -> str:
        return cls.re_number

class Length(Quantity):
    def __init__(self, value: float | str, unit: str | None=None, display_unit: str | None=None):
        super().__init__(value, unit, display_unit)

    unit: ClassVar[str] = "m"
    unit_variants = {
        "dm": 0.1,
        "cm": 0.01,
        "mm": 0.001
    }

class Percentage(Quantity):
    def __init__(self, value: float | str, unit: str | None=None, display_unit: str | None=None):
        super().__init__(value, unit, display_unit)

    unit: ClassVar[str] = ""
    unit_variants = {
        "%": 0.01,
    }
    display_unit: str = "%"

class Angle(Quantity):
    def __init__(self, value: float | str, unit: str | None=None, display_unit: str | None=None):
        super().__init__(value, unit, display_unit)

    unit: ClassVar[str] = "rad"
    unit_variants = {
        "deg": math.pi/180,
        "°": math.pi/180,
    }
    display_unit: str = "°"

a=Quantity(2)
b=Length(2)
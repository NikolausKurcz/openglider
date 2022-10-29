from __future__ import annotations

from typing import Any, Dict, Generic, ItemsView, Iterator, List, Optional, TypeVar

from openglider.utils.colors import Color, colorwheel
from openglider.utils.dataclass import Field, dataclass

ListType = TypeVar("ListType")

colors = colorwheel(5)

@dataclass
class SelectionListItem(Generic[ListType]):
    element: ListType
    active: bool
    color: Color
    name: str

    def __json__(self) -> Dict[str, Any]:
        return {
            "element": self.element,
            "active": self.active,
            "color": self.color.hex(),
            "name": self.name
        }
    
    @classmethod
    def __from_json__(cls, **dct: Dict[str, Any]) -> SelectionListItem:
        dct["color"] = Color.parse_hex(dct["color"])  # type: ignore
        return cls(**dct)  # type: ignore

    def __hash__(self) -> int:
        return hash(self.element)


@dataclass
class SelectionList(Generic[ListType]):
    elements: Dict[str, SelectionListItem[ListType]]=Field(default_factory=lambda: {})
    selected_element: Optional[str] = None

    def get_selected(self) -> Optional[ListType]:
        elem = self.get_selected_wrapped()

        if elem:
            return elem.element
        
        return None
        
    def get_selected_wrapped(self) -> Optional[SelectionListItem[ListType]]:
        if self.selected_element is not None and self.selected_element in self:
            return self.elements[self.selected_element]
        
        return None
    
    def get_active(self) -> List[ListType]:
        result = []

        for name, element in self.elements.items():
            if self.selected_element == name or element.active:
                result.append(element.element)
        
        return result
    
    def filter_active(self) -> Iterator[SelectionListItem[ListType]]:
        for name, element in self.elements.items():
            if self.selected_element == name or element.active:
                yield element
    
    def get_all(self) -> List[ListType]:
        return [e.element for e in self.elements.values()]
    
    def get(self, name: str) -> ListType:
        if name not in self:
            raise ValueError(f"no element named {name}")
        
        return self.elements[name].element
    
    def add(self, name: str, obj: ListType, color: Color=None, select: bool=True) -> None:
        self.elements[name] = SelectionListItem(
            element=obj,
            active=False,
            color=color or colors[len(self.elements)%len(colors)],
            name=name
        )
        if select:
            self.selected_element = name

    def get_name(self, element: SelectionListItem[ListType]) -> str:
        for name, element2 in self.elements.items():
            if element is element2:
                return name
            
        raise ValueError(f"item not in list: {element}")
    
    def remove(self, name: str) -> None:
        if name not in self:
            raise ValueError(f"{name} not in list: {self}")
        
        self.elements.pop(name)
        if self.selected_element == name:
            self.selected_element = None
    
    def reload(self) -> None:
        if self.selected_element in self.elements:
            self.selected_element = self.elements[self.selected_element].name
        else:
            self.selected_element = None
            
        self.elements = {
            element.name: element for element in self.elements.values()
        }
    
    def __iter__(self) -> Iterator[ListType]:
        for name in self.elements:
            yield self.elements[name].element
    
    def __len__(self) -> int:
        return len(self.elements)
    
    def __getitem__(self, name: str) -> SelectionListItem[ListType]:
        return self.elements[name]
    
    def __setitem__(self, name: str, item: ListType) -> None:
        if name in self:
            self.elements[name].element = item
        else:
            self.add(name, item)
    
    def __contains__(self, item: str) -> bool:
        return item in self.elements
    
    def items(self) -> ItemsView[str, SelectionListItem[ListType]]:
        return self.elements.items()

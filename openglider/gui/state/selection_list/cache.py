from openglider.gui.state.selection_list.list import SelectionList, SelectionListItem
from openglider.utils.dataclass import dataclass
from typing import Any, TypeVar, Generic

ListType = TypeVar("ListType")
CacheListType = TypeVar("CacheListType")

@dataclass
class ChangeSet(Generic[ListType]):
    active: list[ListType]

    added: list[ListType]
    removed: list[ListType]


class Cache(Generic[ListType, CacheListType]):
    elements: SelectionList[ListType, SelectionListItem[ListType]]
    cache: dict[str, CacheListType]
    cache_hashes: dict[str, int]
    cache_reference: int | None
    cache_last_active: list[str]

    update_on_color_change = True
    update_on_name_change = True
    update_on_reference_change = False

    def __init__(self, elements: SelectionList[ListType, SelectionListItem[ListType]]):
        self.elements = elements

        self.cache = {}
        self.cache_hashes = {}
        self.cache_last_active = []
        self.cache_reference = None

    def clear(self) -> None:
        self.cache = {}
        self.cache_hashes = {}

    def get_object(self, element: str) -> CacheListType:
        """
        Get the cached object
        """
        raise NotImplementedError()
    
    def _get_object_hash(self, element: str) -> int:
        hash_workload: list[Any] = [self.elements[element].element]
        if self.update_on_color_change:
            hash_workload += self.elements[element].color
        if self.update_on_name_change:
            hash_workload += self.elements[element].name

        return hash(tuple(hash_workload))

    
    def _get_object(self, element: str) -> tuple[CacheListType, bool]:
        obj_hash = self._get_object_hash(element)
        is_outdated = element not in self.cache_hashes or obj_hash != self.cache_hashes[element]

        if is_outdated:
            obj = self.get_object(element)
            self.cache[element] = obj
            self.cache_hashes[element] = obj_hash
        
        return self.cache[element], is_outdated

    
    def get_selected(self) -> CacheListType:
        if self.elements.selected_element is None:
            raise ValueError("no selected element")
        return self._get_object(self.elements.selected_element)[0]
    
    def get_update(self) -> ChangeSet[CacheListType]:
        changeset: ChangeSet[CacheListType] = ChangeSet([],[],[])
        active_names = []

        if self.update_on_reference_change:
            hash = None
            if self.elements.selected_element is not None:
                hash = self._get_object_hash(self.elements.selected_element)
            if hash != self.cache_reference:
                self.cache_reference = hash
                self.cache_hashes.clear()

        # move the selected to the first position
        items = self.elements.elements.copy()
        items_lst = []
        if self.elements.selected_element:
            value = items.pop(self.elements.selected_element)
            items_lst.append((self.elements.selected_element, value))
        
        for name, elem in items.items():
            items_lst.append((name, elem))
        
        for element_name, element in items_lst:
            old_obj = self.cache.get(element_name)
            is_active = element.active or self.elements.selected_element == element_name

            if is_active:
                active_names.append(element_name)
                obj, outdated = self._get_object(element_name)

                changeset.active.append(obj)

                if outdated:
                    changeset.added.append(obj)
                    if old_obj is not None:
                        changeset.removed.append(old_obj)
                elif element_name not in self.cache_last_active:
                    changeset.added.append(obj)
            
            else:
                if element_name in self.cache_last_active and old_obj is not None:
                    changeset.removed.append(old_obj)
        
        existing_names = list(self.elements.elements.keys())
        cached_names = list(self.cache)

        for name in cached_names:
            if name not in existing_names:
                cache_elem = self.cache.pop(name)
                changeset.removed.append(cache_elem)
                self.cache_hashes.pop(name)
        
        self.cache_last_active = active_names

        return changeset            

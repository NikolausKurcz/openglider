from typing import Any, Dict, List

from openglider.glider.cell.diagonals import DiagonalRib, DiagonalSide, TensionLine, TensionStrap
from openglider.glider.curve import GliderCurveType
from openglider.glider.parametric.table.base import CellTable, Keyword
from openglider.glider.parametric.table.base.dto import DTO, CellTuple
from openglider.glider.parametric.table.base.parser import Parser
from openglider.utils.table import Table

import logging

from openglider.vector.unit import Length, Percentage

logger = logging.getLogger(__name__)

class QRDTO(DTO):
    position: CellTuple[Percentage]
    width: CellTuple[Percentage | Length]
    height: CellTuple[Percentage]

    def get_object(self) -> DiagonalRib:
        left_side = DiagonalSide(center=self.position.first, width=self.width.first, height=self.height.first.si)
        right_side = DiagonalSide(center=self.position.second, width=self.width.second, height=self.height.second.si)

        return DiagonalRib(left_side, right_side)
    
class DiagonalDTO(QRDTO):
    material_code: str

    def get_object(self) -> DiagonalRib:
        diagonal = super().get_object()
        diagonal.material_code = self.material_code

        return diagonal

class StrapDTO(DTO):
    position: CellTuple[Percentage]
    width: Percentage | Length

    def get_object(self) -> TensionStrap:
        return TensionStrap(self.position.first, self.position.second, self.width)
    
class TensionLineDTO(DTO):
    position: CellTuple[Percentage]

    def get_object(self) -> TensionLine:
        return TensionLine(self.position.first, self.position.second)

class DiagonalTable(CellTable):

    def __init__(self, table: Table=None, file_version: int=None, migrate: bool=False):
        if file_version == 1:
            pass
            # height (0,1) -> (-1,1)
            # TODO
            #height1 = height1 * 2 - 1
            #height2 = height2 * 2 - 1

        super().__init__(table, migrate_header=migrate)


    dtos = {
        "QR": QRDTO,
        "DIAGONAL": DiagonalDTO
    }

class StrapTable(CellTable):
    dtos = {
        "STRAP": StrapDTO,
        "VEKTLAENGE": TensionLineDTO
    }

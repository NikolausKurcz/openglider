import logging
from typing import Any
from openglider.glider.parametric.table.base.table import ElementTable
from openglider.glider.parametric.table.lines import LineSetTable

from openglider.glider.parametric.table.attachment_points import AttachmentPointTable, CellAttachmentPointTable
from openglider.glider.parametric.table.cell.ballooning import BallooningModifierTable
from openglider.glider.parametric.table.cell.cuts import CutTable
from openglider.glider.parametric.table.cell.diagonals import DiagonalTable, StrapTable
from openglider.glider.parametric.table.cell.miniribs import MiniRibTable
from openglider.glider.parametric.table.curve import CurveTable
from openglider.glider.parametric.table.base import TableType
from openglider.glider.parametric.table.material import CellClothTable, RibClothTable
from openglider.glider.parametric.table.rib.holes import HolesTable
from openglider.glider.parametric.table.rib.profile import ProfileModifierTable
from openglider.glider.parametric.table.rib.rib import SingleSkinTable
from openglider.glider.parametric.table.rigidfoil import CellRigidTable, RibRigidTable
from openglider.utils.table import Table
from openglider.version import __version__

logger = logging.getLogger(__name__)


class GliderTables:
    curves: CurveTable
    cuts: CutTable
    ballooning_modifiers: BallooningModifierTable
    holes: HolesTable
    diagonals: DiagonalTable
    straps: StrapTable
    rigidfoils_rib: RibRigidTable
    rigidfoils_cell: CellRigidTable
    material_cells: CellClothTable
    material_ribs: RibClothTable
    miniribs: MiniRibTable
    rib_modifiers: SingleSkinTable
    profile_modifiers: ProfileModifierTable
    attachment_points_rib: AttachmentPointTable
    attachment_points_cell: CellAttachmentPointTable
    lines: LineSetTable

    def __init__(self, **kwargs: Any):
        used_names = []

        for name, _cls in self.__annotations__.items():
            if name in kwargs:
                table = kwargs[name]
                used_names.append(name)
            else:
                table = _cls()
            
            setattr(self, name, table)

        for name in kwargs:
            if name not in used_names:
                logger.warning(f"unused table/element kwarg: {name}")
        
    
    def __json__(self) -> dict[str, Any]:
        dct = {}
        for name in self.__annotations__:
            dct[name] = getattr(self, name)
        
        return dct
    
    @classmethod
    def describe(cls) -> str:
        text = "# glider tables\n\n"
        for table_type in TableType:
            text += f"## {table_type.value}\n\n"

            for name, _cls in cls.__annotations__.items():
                if issubclass(_cls, ElementTable) and _cls.table_type == table_type:
                    text += f"### {name}\n\n"

                    for keyword_name, keyword in _cls.keywords.items():
                        text += f"- {keyword_name}\n"
                        text += f"{keyword.describe()}\n"

                    for dto_name, dto in _cls.dtos.items():
                        text += f"- {dto_name}\n"
                        text += f"{dto.describe_text()}\n"
                    
                    text += "\n\n"

        return text
    
    def get_rib_sheet(self) -> Table:
        table = Table()
        table.name = "Rib Elements"
        table[0,0] = f"V_{__version__}"

        table.append_right(self.profile_modifiers.table)
        table.append_right(self.holes.table)
        table.append_right(self.attachment_points_rib.table)
        table.append_right(self.rigidfoils_rib.table)
        table.append_right(self.rib_modifiers.table)
        table.append_right(self.material_ribs.table)

        for i in range(1, table.num_rows+1):
            table[i, 0] = str(i)

        return table
    
    def get_cell_sheet(self) -> Table:
        table = Table()
        table.name = "Cell Elements"
        table[0,0] = f"V_{__version__}"

        table.append_right(self.cuts.table)
        table.append_right(self.diagonals.table)
        table.append_right(self.rigidfoils_cell.table)
        table.append_right(self.straps.table)
        table.append_right(self.material_cells.table)
        table.append_right(self.miniribs.table)
        table.append_right(self.attachment_points_cell.table)
        table.append_right(self.ballooning_modifiers.table)

        for i in range(1, table.num_rows+1):
            table[i, 0] = str(i)

        return table
    
    def get_all_tables(self) -> list[Table]:
        tables = []

        for name in self.__annotations__.keys():
            table = getattr(self, name).table
            table.name = name
            
            tables.append(table)
        
        return tables


if __name__ == "__main__":
    import pathlib
    filename = pathlib.Path(__file__).absolute().parent / "Readme.md"
    with open(filename, "w") as outfile:
        print("writing readme")
        outfile.write(GliderTables.describe())

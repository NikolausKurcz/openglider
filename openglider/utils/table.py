from __future__ import annotations

import copy
import re
from typing import Any, Union

try:
    import pyexcel_ods
except ImportError:
    import pyexcel_ods3 as pyexcel_ods

import ezodf

CellIndex = Union[tuple[int, int], str]

class Table:
    rex = re.compile(r"([A-Z]*)([0-9]*)")
    format_float_digits = 4
    name: str=""

    dct: dict[str, Any]

    @classmethod
    def str_decrypt(cls, str: str) -> tuple[int, int]:
        result = cls.rex.match(str.upper())
        if result:
            column, row = result.groups()
            column_no = 0
            for i, character in enumerate(column[::-1]):
                column_no += (26**i)*(ord(character)-64)

            row_no = int(row)

            return column_no-1, row_no-1

        raise ValueError

    @classmethod
    def str_encrypt(cls, column: int, row: int) -> str:

        return cls.column_to_char(column + 1) + str(row + 1)

    @classmethod
    def column_to_char(cls, x: int) -> str:
        base = 26
        out = ""
        #x -= 1
        while x:
            out += chr(((x-1) % base)+65)
            x = int((x-1)/base)
        return out[::-1]

    def __init__(self, rows: int=0, columns: int=0, name: str=None):
        self.dct = {}
        self.num_rows = rows
        self.num_columns = columns
        self.name=name or ""
    
    def __json__(self) -> dict[str, Any]:
        return {
            "dct": self.dct
        }
    
    @classmethod
    def __from_json__(cls, dct: dict[str, Any]) -> Table:
        table = cls()
        table.dct = dct

        for key in dct:
            column, row = cls.str_decrypt(key)

            table.num_rows = max(table.num_rows, row+1)
            table.num_columns = max(table.num_columns, column+1)
        
        return table


    def __setitem__(self, key: CellIndex , value: Any) -> None:
        if isinstance(key, tuple):
            row_no, column_no = key
        else:
            column_no, row_no = self.str_decrypt(key)
        self.set_value(column_no, row_no, value)

    def __getitem__(self, item: CellIndex) -> Any:
        if isinstance(item, tuple):
            row_no, column_no = item
            item = self.str_encrypt(column_no, row_no)
        return self.dct.get(item, None)

    def get_columns(self, from_i: int, to_j: int | None) -> Table:
        if to_j is None:
            to_j = self.num_columns
        new_table = self.__class__(self.num_rows, to_j-from_i)
        for i in range(from_i, to_j):
            for row in range(self.num_rows):
                item = self.str_encrypt(i, row)
                if item in self.dct:
                    new_table.set_value(i-from_i, row, self.dct[item])
        
        return new_table
    
    def get_rows(self, from_row: int, to_row: int | None) -> Table:
        if to_row is None:
            to_row = self.num_rows
        row_count = to_row - from_row
        new_table = Table(row_count, self.num_columns, name=self.name)

        for i in range(from_row, to_row):
            for column in range(self.num_columns):
                item = self.str_encrypt(column, i)
                if item in self.dct:
                    new_table.set_value(column, i-from_row, self.dct[item])
        
        return new_table

    def __isub__(self, other: Table) -> Table:
        import numbers
        for key in other.dct:
            zwei = other[key]

            if key in self.dct:
                eins = self[key]
            else:
                if isinstance(zwei, numbers.Number):
                    eins = 0
                else:
                    eins = ""

            if isinstance(eins, numbers.Number) and isinstance(zwei, numbers.Number):
                self[key] = eins - zwei  # type: ignore
            else:
                self[key] = str(eins) + " - " + str(zwei)

        return self

    def __sub__(self, other: Table) -> Table:
        cpy = copy.deepcopy(self)
        cpy -= other

        return cpy

    def copy(self) -> Table:
        return copy.deepcopy(self)

    def set_value(self, column_no: int, row_no: int, value: Any) -> None:
        self.num_columns = max(column_no+1, self.num_columns)
        self.num_rows = max(row_no+1, self.num_rows)
        key = self.str_encrypt(column_no, row_no)
        self.dct[key] = value

    def insert_row(self, row: list[Any], row_no: int | None=None) -> None:
        if row_no is None:
            row_no = self.num_rows
        for i, el in enumerate(row):
            self.set_value(i, row_no, el)

    def get(self, column_no: int, row_no: int) -> Any:
        key = self.str_encrypt(column_no, row_no)
        return self.dct.get(key, None)

    def append_right(self, table: Table, space: int=0) -> None:
        old_column_no = self.num_columns
        
        columns_to_add = table.num_columns
        rows_to_add = table.num_rows

        for row_no in range(rows_to_add):
            for column_no in range(columns_to_add):
                value = table.get(column_no, row_no)
                if value is not None:
                    self.set_value(old_column_no+column_no+space, row_no, value)

    def append_bottom(self, table: Table, space: int=0) -> None:
        total_rows = self.num_rows
        for row_no in range(table.num_rows):
            for column_no in range(table.num_columns):
                value = table.get(column_no, row_no)
                if value is not None:
                    self.set_value(column_no, total_rows+row_no+space, value)

    def get_ods_sheet(self, name: str=None) -> ezodf.Table:
        rows = max(1, self.num_rows)
        columns = max(1, self.num_columns)
        ods_sheet = ezodf.Table(size=(rows, columns))
        for key in self.dct:
            column, row = self.str_decrypt(key)
            if self.dct[key] is not None:
                ods_sheet[row, column].set_value(self.dct[key])

        if name:
            ods_sheet.name = name
        elif self.name is not None:
            ods_sheet.name = self.name
        else:
            ods_sheet.name = "table"

        return ods_sheet

    def save(self, path: str) -> ezodf.document.PackagedDocument:
        doc = ezodf.newdoc(doctype="ods", filename=path)
        doc.sheets.append(self.get_ods_sheet())
        doc.save()
        return doc
    
    @classmethod
    def save_tables(self, tables: list[Table], path: str) -> ezodf.document.PackagedDocument:
        doc = ezodf.newdoc(doctype="ods", filename=path)

        for table in tables:
            doc.sheets.append(table.get_ods_sheet())
        doc.save()
        return doc

    @classmethod
    def load(cls, path: str) -> list[Table]:
        data: dict[str, list[list[Any]]] = pyexcel_ods.get_data(path)

        sheets = [cls.from_list(sheet, name=name) for name, sheet in data.items()]
        
        return sheets

    @classmethod
    def from_ods_sheet(cls, sheet: ezodf.Sheet) -> Table:
        num_rows = sheet.nrows()
        num_cols = sheet.ncols()
        table = cls()

        for row in range(num_rows):
            for col in range(num_cols):
                value = sheet.get_cell([row, col]).value
                if value is not None:
                    table[row, col] = value

        return table

    @classmethod
    def from_list(cls, lst: list[list[Any]], name: str | None=None) -> Table:
        table = cls(name=name)

        for row_no, row in enumerate(lst):
            for col_no, value in enumerate(row):
                if value not in ("", None):
                    table[row_no, col_no] = value
        
        return table

    def get_markdown_table(self) -> str:
        table = self.copy()
        column_widths = []
        num_columns = table.num_columns
        num_rows = table.num_rows
        float_str = f"{{:.{self.format_float_digits}f}}"

        for column_no in range(num_columns):
            column_width = 0
            for row_no in range(num_rows):
                value = table[row_no, column_no]
                if value is not None:
                    if type(value) is float:
                        str_value = float_str.format(value)
                        table[row_no, column_no] = str_value
                    else:
                        str_value = str(value)
                        table[row_no, column_no] = str_value
                    
                    column_width = max(column_width, len(str_value))
                else:
                    table[row_no, column_no] = ""
            
            column_widths.append(column_width)
        
        text = ""
        for row_no in range(num_rows):
            text += "|"
            for column_no in range(num_columns):
                width = column_widths[column_no]
                value = table[row_no, column_no] or ""

                text += " " * (width - len(value) + 1)
                text += value
                text += " |"
            
            text += "\n"

        return text

    def _repr_html_(self) -> str:
        html = "<table><thead><td></td>"
        for column_no in range(self.num_columns):
            html += f"<td>{self.column_to_char(column_no + 1)}</td>"

        html += "</thead>"
        for row_no in range(self.num_rows):
            html += f"<tr><td>{row_no+1}</td>"
            for column_no in range(self.num_columns):
                ident = self.str_encrypt(column_no, row_no)
                value = self.dct.get(ident, "")
                if isinstance(value, float):
                    value = round(value, self.format_float_digits)
                html += f"<td>{value}</td>"
            html += "</tr>"

        html += "</table>"

        return html


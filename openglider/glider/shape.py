from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, TypeAlias

import euklid
from openglider.vector.drawing import Layout, PlotPart
from openglider.vector.unit import Percentage

if TYPE_CHECKING:
    from openglider.glider.cell.panel import Panel


logger = logging.getLogger(__name__)

V2: TypeAlias = euklid.vector.Vector2D

class Shape:
    def __init__(self, front: euklid.vector.PolyLine2D, back: euklid.vector.PolyLine2D) -> None:
        # TODO: REMOVE
        if not isinstance(front, euklid.vector.PolyLine2D):
            front = euklid.vector.PolyLine2D(list(front))
        if not isinstance(back, euklid.vector.PolyLine2D):
            back = euklid.vector.PolyLine2D(list(back))
        self.front = front
        self.back = back

    @property
    def has_center_cell(self) -> bool:
        return abs(self.front.nodes[0][0]) > 1e-5 and abs(self.back.nodes[0][0]) > 1e-5

    def get_point(self, x: float | int, y: float | Percentage) -> euklid.vector.Vector2D:
        front = self.front.get(x)
        back = self.back.get(x)

        return front + (back-front) *  float(y)
    
    def get_baseline(self, position: Percentage) -> euklid.vector.PolyLine2D:
        points = []
        for front, back in zip(self.front.nodes, self.back.nodes):
            points.append(
                front + (back - front) * position.si
            )

        return euklid.vector.PolyLine2D(points)

    def get_panel(self, cell_no: int, panel: Panel) -> tuple[V2, V2, V2, V2]:
        p1 = self.get_point(cell_no, panel.cut_front.x_left)
        p2 = self.get_point(cell_no, panel.cut_back.x_left)
        p3 = self.get_point(cell_no+1, panel.cut_back.x_right)
        p4 = self.get_point(cell_no+1, panel.cut_front.x_right)

        return p1, p2, p3, p4

    @property
    def cell_no(self) -> int:
        return len(self.front) - 1

    @property
    def rib_no(self) -> int:
        return len(self.front)

    @property
    def ribs(self) -> list[tuple[euklid.vector.Vector2D, euklid.vector.Vector2D]]:
        return [(self.front.get(x), self.back.get(x)) for x in range(len(self.front))]

    @property
    def ribs_front_back(self) -> tuple[
        list[tuple[V2, V2]],
        euklid.vector.PolyLine2D,
        euklid.vector.PolyLine2D    
    ]:
        return (self.ribs, self.front, self.back)

    @property
    def span(self) -> float:
        return self.front.nodes[-1][0]
    
    @span.setter
    def span(self, span: float) -> None:
        span_old = self.span
        self.scale(span/span_old, 1)


    @property
    def chords(self) -> list[float]:
        return [(p1-p2).length() for p1, p2 in zip(self.front, self.back)]

    @property
    def cell_widths(self) -> list[float]:
        return [p2[0]-p1[0] for p1, p2 in zip(self.front.nodes[:-1], self.front.nodes[1:])]

    @property
    def area(self) -> float:
        front, back = self.front, self.back
        area = 0.
        for i in range(len(self.front) - 1):
            l = (front.get(i)[1] - back.get(i)[1]) + (front.get(i+1)[1] - back.get(i+1)[1])
            area += l * (front.get(i+1)[0] - front.get(i)[0]) / 2
        return area
    
    @area.setter
    def area(self, area: float) -> None:
        factor = math.sqrt(area / self.area)

        self.scale(factor, factor)

    def scale(self, x: float=1, y: float =1.) -> Shape:
        self.front = self.front.scale(euklid.vector.Vector2D([x, y]))
        self.back = self.back.scale(euklid.vector.Vector2D([x, y]))

        return self
    
    def copy(self) -> Shape:
        return Shape(self.front.copy(), self.back.copy())

    def copy_complete(self) -> Shape:
        front = self.front.mirror().reverse()
        back = self.back.mirror().reverse()

        if front.nodes[-1][0] != 0:
            start = 2
        else:
            start = 1

        front_nodes = front.nodes + self.front.copy().nodes[start:]
        back_nodes = back.nodes + self.back.copy().nodes[start:]

        return Shape(euklid.vector.PolyLine2D(front_nodes), euklid.vector.PolyLine2D(back_nodes))

    def _repr_svg_(self) -> str:
        da = Layout()
        for cell_no in range(self.cell_no):
            points = [
                self.get_point(cell_no, 0),
                self.get_point(cell_no, 1),
                self.get_point(cell_no+1, 1),
                self.get_point(cell_no+1, 0)
            ]
            points.append(points[0])
            da.parts.append(PlotPart(marks=[euklid.vector.PolyLine2D(points)]))

        return da._repr_svg_()

import euklid
import logging
import math

from openglider.vector.drawing import PlotPart, Layout

logger = logging.getLogger(__name__)


class Shape(object):
    def __init__(self, front: euklid.vector.PolyLine2D, back: euklid.vector.PolyLine2D):
        # TODO: REMOVE
        if not isinstance(front, euklid.vector.PolyLine2D):
            front = euklid.vector.PolyLine2D(list(front))
        if not isinstance(back, euklid.vector.PolyLine2D):
            back = euklid.vector.PolyLine2D(list(back))
        self.front = front
        self.back = back

    def get_point(self, x, y):
        front = self.front.get(x)
        back = self.back.get(x)

        return front + (back-front) *  y

    def get_panel(self, cell_no, panel):
        p1 = self.get_point(cell_no, panel.cut_front["left"])
        p2 = self.get_point(cell_no, panel.cut_back["left"])
        p3 = self.get_point(cell_no+1, panel.cut_back["right"])
        p4 = self.get_point(cell_no+1, panel.cut_front["right"])

        return p1, p2, p3, p4

    @property
    def cell_no(self):
        return len(self.front) - 1

    @property
    def rib_no(self):
        return len(self.front)

    @property
    def ribs(self):
        return [[self.front.get(x), self.back.get(x)] for x in range(len(self.front))]

    @property
    def ribs_front_back(self):
        return [self.ribs, self.front, self.back]

    @property
    def span(self):
        return self.front.nodes[-1][0]
    
    @span.setter
    def span(self, span):
        span_old = self.span
        self.scale(span/span_old, 1)


    @property
    def chords(self):
        return [(p1-p2).length() for p1, p2 in zip(self.front, self.back)]

    @property
    def cell_widths(self):
        return [p2[0]-p1[0] for p1, p2 in zip(self.front.nodes[:-1], self.front.nodes[1:])]

    @property
    def area(self):
        front, back = self.front, self.back
        area = 0
        for i in range(len(self.front) - 1):
            l = (front.get(i)[1] - back.get(i)[1]) + (front.get(i+1)[1] - back.get(i+1)[1])
            area += l * (front.get(i+1)[0] - front.get(i)[0]) / 2
        return area
    
    @area.setter
    def area(self, area):
        area_old = self.area
        factor = math.sqrt(area / self.area)

        self.scale(factor, factor)

    def scale(self, x=1, y=1):
        logger.warning(f"deprecation: Shape scale!")
        self.front = self.front.scale([x, y])
        self.back = self.back.scale([x, y])

        return self
    
    def copy(self):
        return Shape(self.front.copy(), self.back.copy())

    def copy_complete(self):
        front = self.front.mirror([0, 0], [0, 1]).reverse()
        back = self.back.mirror([0, 0], [0, 1]).reverse()

        if front.nodes[-1][0] != 0:
            start = 2
        else:
            start = 1

        front_nodes = front.nodes + self.front.copy().nodes[start:]
        back_nodes = back.nodes + self.back.copy().nodes[start:]

        return Shape(euklid.vector.PolyLine2D(front_nodes), euklid.vector.PolyLine2D(back_nodes))

    def _repr_svg_(self):
        da = Layout()
        for cell_no in range(self.cell_no):
            points = [
                self.get_point(cell_no, 0),
                self.get_point(cell_no, 1),
                self.get_point(cell_no+1, 1),
                self.get_point(cell_no+1, 0)
            ]
            points.append(points[0])
            da.parts.append(PlotPart(marks=[points]))

        return da._repr_svg_()


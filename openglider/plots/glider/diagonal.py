import logging
import math
from typing import Tuple

import euklid
from openglider.glider.cell import DiagonalRib
from openglider.plots.glider.config import PatternConfig
from openglider.plots.usage_stats import Material, MaterialUsage
from openglider.vector.drawing import Layout, PlotPart
from openglider.vector.text import Text


logger = logging.getLogger(__name__)


class DribPlot(object):
    DefaultConf = PatternConfig

    def __init__(self, drib: DiagonalRib, cell, config):
        self.drib: DiagonalRib = drib
        self.cell = cell
        self.config = self.DefaultConf(config)

        self.left, self.right = self.drib.get_flattened(self.cell)

        self.left_out = self.left.offset(-self.config.allowance_general)
        self.right_out = self.right.offset(self.config.allowance_general)

        #print("l", len(self.left), len(self.left_out))
        #print("r", len(self.right), len(self.right_out))

    def get_left(self, x):
        return self.get_p1_p2(x, side=0)

    def get_right(self, x):
        return self.get_p1_p2(x, side=1)

    def _is_valid(self, x, side=0):
        if side == 0:
            front = self.drib.left_front
            back = self.drib.left_back
        else:
            front = self.drib.right_front
            back = self.drib.right_back

        if (front[1], back[1]) not in ((-1, -1), (1, 1)):
            return False

        if front[1] > 0:
            # swapped sides
            boundary = [-front[0], -back[0]]
        else:
            boundary = [front[0], back[0]]
        boundary.sort()

        if not boundary[0] <= x <= boundary[1]:
            return False

        return True

    def get_p1_p2(self, x, side=0):
        assert self._is_valid(x, side=side)

        if side == 0:
            front = self.drib.left_front
            back = self.drib.left_back
            rib = self.cell.rib1
            inner = self.left
            outer = self.left_out
        else:
            front = self.drib.right_front
            back = self.drib.right_back
            rib = self.cell.rib2
            inner = self.right
            outer = self.right_out

        assert front[0] <= x <= back[0]

        foil = rib.profile_2d
        # -1 -> lower, 1 -> upper
        foil_side = 1 if front[1] == -1 else -1

        x1 = front[0] * foil_side
        x2 = x * foil_side

        ik_1 = foil(x1)
        ik_2 = foil(x2)
        length = foil.curve.get(ik_1, ik_2).get_length() * rib.chord

        ik_new = inner.walk(0, length)
        return inner.get(ik_new), outer.get(ik_new)

    def _insert_attachment_points(self, plotpart, attachment_points=None):
        attachment_points = attachment_points or []

        for attachment_point in attachment_points:
            if not hasattr(attachment_point, "rib"):
                continue
            x = attachment_point.rib_pos
            if attachment_point.rib is self.cell.rib1:
                if not self._is_valid(x, side=0):
                    continue
                p1, p2 = self.get_left(attachment_point.rib_pos)
            elif attachment_point.rib is self.cell.rib2:
                if not self._is_valid(x, side=1):
                    continue

                p1, p2 = self.get_right(attachment_point.rib_pos)
            else:
                continue

            plotpart.layers["marks"] += self.config.marks_attachment_point(p1, p2)
            plotpart.layers["L0"] += self.config.marks_laser_attachment_point(p1, p2)

    def _insert_text(self, plotpart, reverse=False):
        if reverse:
            node_index = -1
        else:
            node_index = 0
        # text_p1 = left_out[0] + self.config.drib_text_position * (right_out[0] - left_out[0])
        plotpart.layers["text"] += Text(" {} ".format(self.drib.name),
                                        self.left.nodes[node_index],
                                        self.right.nodes[node_index],
                                        size=self.config.drib_allowance_folds * 0.6,
                                        height=0.6,
                                        valign=0.6).get_vectors()

    def flatten(self, attachment_points=None):
        return self._flatten(attachment_points, self.drib.num_folds)

    def _flatten(self, attachment_points, num_folds):
        plotpart = PlotPart(material_code=self.drib.material_code, name=self.drib.name)

        if num_folds > 0:
            alw2 = self.config.drib_allowance_folds
            cut_front = self.config.cut_diagonal_fold(-alw2, num_folds=num_folds)
            cut_back = self.config.cut_diagonal_fold(alw2, num_folds=num_folds)
            
            cut_front_result = cut_front.apply([[self.left, 0], [self.right, 0]], self.left_out, self.right_out)
            cut_back_result = cut_back.apply([[self.left, len(self.left) - 1], [self.right, len(self.right) - 1]], self.left_out, self.right_out)
            
            plotpart.layers["cuts"] += [self.left_out.get(cut_front_result.index_left, cut_back_result.index_left) +
                                        cut_back_result.curve +
                                        self.right_out.get(cut_back_result.index_right, cut_front_result.index_right) +
                                        cut_front_result.curve.reverse()
            ]

        else:
            p1 = self.left_out.cut(self.left.get(0), self.right.get(0), 0)[0]
            p2 = self.left_out.cut(self.left.get(len(self.left)-1), self.right.get(len(self.right)-1), len(self.left_out))[0]
            p3 = self.right_out.cut(self.left.get(0), self.right.get(0), 0)[0]
            p4 = self.right_out.cut(self.left.get(len(self.left)-1), self.right.get(len(self.right)-1), len(self.right_out))[0]

            #outer = self.left_out.get(p1, p2)
            #outer += self.right_out.get(p3,p4).reverse()
            #outer += euklid.vector.PolyLine2D([self.left_out.get(p1)])

            outer = self.left_out.copy()
            outer += euklid.vector.PolyLine2D([self.left.nodes[-1]])
            outer += euklid.vector.PolyLine2D([self.right.nodes[-1]])
            outer += self.right_out.reverse()
            outer += euklid.vector.PolyLine2D([self.right.nodes[0]])
            outer += euklid.vector.PolyLine2D([self.left.nodes[0]])
            outer += euklid.vector.PolyLine2D([self.left_out.nodes[0]])
            #outer += euklid.vector.PolyLine2D([self.left_out.get(p1)])
            plotpart.layers["cuts"].append(outer)

        for curve in self.drib.get_holes(self.cell)[0]:
            plotpart.layers["cuts"].append(curve)

        plotpart.layers["marks"].append(euklid.vector.PolyLine2D([self.left.get(0), self.right.get(0)]))
        plotpart.layers["marks"].append(euklid.vector.PolyLine2D([self.left.get(len(self.left) - 1), self.right.get(len(self.right) - 1)]))

        plotpart.layers["stitches"] += [self.left, self.right]

        self._insert_attachment_points(plotpart, attachment_points)


        if self.drib.get_average_x() > 0:
            p1 = euklid.vector.Vector2D([0, 0])
            p2 = euklid.vector.Vector2D([1, 0])
            plotpart = plotpart.mirror(p1, p2)
            self._insert_text(plotpart)
        else:
            self._insert_text(plotpart, reverse=True)
        
        self.plotpart = plotpart
        return plotpart
    
    def get_material_usage(self) -> MaterialUsage:
        dwg = self.plotpart

        curves = dwg.layers["envelope"].polylines
        usage = MaterialUsage()
        material = Material(weight=38, name="dribs")

        if curves:
            area = curves[0].get_area()
        
            for curve in self.drib.get_holes(self.cell)[0]:
                area -= curve.get_area()
                
            usage.consume(material, area)

        return usage


class StrapPlot(DribPlot):
    def flatten(self, attachment_points=None):
        return self._flatten(attachment_points, self.config.strap_num_folds)

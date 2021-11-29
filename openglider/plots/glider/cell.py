import logging
import math
from typing import Tuple

import euklid
import numpy as np
import openglider.utils
import openglider.vector.projection as projection
from openglider.airfoil import get_x_value
from openglider.glider.cell import DiagonalRib, Panel, PanelCut
from openglider.plots.glider.config import PatternConfig
from openglider.plots.usage_stats import Material, MaterialUsage
from openglider.vector.drawing import Layout, PlotPart
from openglider.vector.text import Text

logger = logging.getLogger(__name__)

class PanelPlot(object):
    DefaultConf = PatternConfig
    plotpart: PlotPart

    def __init__(self, panel: Panel, cell, flattended_cell, config=None):
        self.panel = panel
        self.cell = cell
        self.config = self.DefaultConf(config)

        self._flattened_cell = flattended_cell

        self.inner = flattended_cell["inner"]
        self.ballooned = flattended_cell["ballooned"]
        self.outer = flattended_cell["outer"]
        self.outer_orig = flattended_cell["outer_orig"]

        self.x_values = self.cell.rib1.profile_2d.x_values

        self.logger = logging.getLogger(r"{self.__class__.__module__}.{self.__class__.__name__}")

    def flatten(self, attachment_points):
        plotpart = PlotPart(material_code=str(self.panel.material), name=self.panel.name)

        _cut_types = PanelCut.CUT_TYPES

        cut_allowances = {
            _cut_types.folded: self.config.allowance_entry_open,
            _cut_types.parallel: self.config.allowance_trailing_edge,
            _cut_types.orthogonal: self.config.allowance_design,
            _cut_types.singleskin: self.config.allowance_entry_open,
            _cut_types.cut_3d: self.config.allowance_design,
            _cut_types.round: self.config.allowance_design
        }

        cut_types = {
            _cut_types.folded: self.config.cut_entry,
            _cut_types.parallel: self.config.cut_trailing_edge,
            _cut_types.orthogonal: self.config.cut_design,
            _cut_types.singleskin: self.config.cut_entry,
            _cut_types.cut_3d: self.config.cut_3d,
            _cut_types.round: self.config.cut_round
        }

        ik_values = self.panel._get_ik_values(self.cell, self.config.midribs, exact=True)

        # get seam allowance
        if self.panel.cut_front.seam_allowance is not None:
            allowance_front = -self.panel.cut_front.seam_allowance
        else:
            allowance_front = -cut_allowances[self.panel.cut_front.cut_type]
        
        if self.panel.cut_back.seam_allowance is not None:
            allowance_back = self.panel.cut_back.seam_allowance
        else:
            allowance_back = cut_allowances[self.panel.cut_back.cut_type]

        # cuts -> cut-line, index left, index right
        cut_front = cut_types[self.panel.cut_front.cut_type](allowance_front)
        cut_back = cut_types[self.panel.cut_back.cut_type](allowance_back)

        inner_front = [(line, ik[0]) for line, ik in zip(self.inner, ik_values)]
        inner_back = [(line, ik[1]) for line, ik in zip(self.inner, ik_values)]

        shape_3d_amount_front = [-x for x in self.panel.cut_front.cut_3d_amount]
        shape_3d_amount_back = self.panel.cut_back.cut_3d_amount

        if self.panel.cut_front.cut_type != _cut_types.cut_3d:
            dist = np.linspace(shape_3d_amount_front[0], shape_3d_amount_front[-1], len(shape_3d_amount_front))
            shape_3d_amount_front = list(dist)

        if self.panel.cut_back.cut_type != _cut_types.cut_3d:
            dist = np.linspace(shape_3d_amount_back[0], shape_3d_amount_back[-1], len(shape_3d_amount_back))
            shape_3d_amount_back = list(dist)

        left = inner_front[0][0].get(inner_front[0][1], inner_back[0][1])
        right = inner_front[-1][0].get(inner_front[-1][1], inner_back[-1][1])

        outer_left = left.offset(-self.config.allowance_general)
        outer_right = right.offset(self.config.allowance_general)

        cut_front_result = cut_front.apply(inner_front, outer_left, outer_right, shape_3d_amount_front)
        cut_back_result = cut_back.apply(inner_back, outer_left, outer_right, shape_3d_amount_back)

        panel_left = outer_left.get(cut_front_result.index_left, cut_back_result.index_left).fix_errors()
        panel_back = cut_back_result.curve.copy()
        panel_right = outer_right.get(cut_back_result.index_right, cut_front_result.index_right).fix_errors()
        panel_front = cut_front_result.curve.copy()

        # spitzer schnitt
        # rechts
        # TODO: FIX!
        # if cut_front_result.index_right >= cut_back_result.index_right:
        #     panel_right = euklid.vector.PolyLine2D([])

        #     _cuts = panel_front.cut_with_polyline(panel_back, startpoint=len(panel_front) - 1)
        #     try:
        #         ik_front, ik_back = next(_cuts)
        #         panel_back = panel_back.get(0, ik_back)
        #         panel_front = panel_front.get(0, ik_front)
        #     except StopIteration:
        #         pass  # todo: fix!!

        # # lechts
        # if cut_front_result.index_left >= cut_back_result.index_left:
        #     panel_left = euklid.vector.PolyLine2D([])

        #     _cuts = panel_front.cut_with_polyline(panel_back, startpoint=0)
        #     try:
        #         ik_front, ik_back = next(_cuts)
        #         panel_back = panel_back.get(ik_back, len(panel_back)-1)
        #         panel_front = panel_front[ik_front, len(panel_back)-1]
        #     except StopIteration:
        #         pass  # todo: fix as well!

        panel_back = panel_back.get(len(panel_back)-1, 0)
        if panel_right:
            panel_right = panel_right.reverse()


        envelope = panel_right + panel_back
        if len(panel_left) > 0:
            envelope += panel_left.reverse()
        envelope += panel_front
        envelope += euklid.vector.PolyLine2D([envelope.nodes[0]])

        plotpart.layers["envelope"].append(envelope)

        if self.config.debug:
            plotpart.layers["debug"].append(euklid.vector.PolyLine2D([line.get(ik) for line, ik in inner_front]))
            plotpart.layers["debug"].append(euklid.vector.PolyLine2D([line.get(ik) for line, ik in inner_back]))
            for front, back in zip(inner_front, inner_back):
                plotpart.layers["debug"].append(front[0].get(front[1], back[1]))

        # sewings
        plotpart.layers["stitches"] += [
            self.inner[0].get(cut_front_result.inner_indices[0], cut_back_result.inner_indices[0]),
            self.inner[-1].get(cut_front_result.inner_indices[-1], cut_back_result.inner_indices[-1])
            ]

        # folding line
        plotpart.layers["marks"] += [
            euklid.vector.PolyLine2D([
                line.get(x) for line, x in zip(self.inner, cut_front_result.inner_indices)
            ]),

            euklid.vector.PolyLine2D([
                line.get(x) for line, x in zip(self.inner, cut_back_result.inner_indices)
            ])
        ]

        # TODO
        if False:
            if panel_right:
                right = euklid.vector.PolyLine2D([panel_front.last()]) + panel_right + euklid.vector.PolyLine2D([panel_back[0]])
                plotpart.layers["cuts"].append(right)

            plotpart.layers["cuts"].append(panel_back)

            if panel_left:
                left = euklid.vector.PolyLine2D([panel_back.last()]) + panel_left + euklid.vector.PolyLine2D([panel_front[0]])
                plotpart.layers["cuts"].append(left)

            plotpart.layers["cuts"].append(panel_front)
        else:
            plotpart.layers["cuts"].append(envelope.copy())

        self._insert_text(plotpart)
        self._insert_controlpoints(plotpart)
        self._insert_attachment_points(plotpart, attachment_points=attachment_points)
        self._insert_diagonals(plotpart)
        self._insert_rigidfoils(plotpart)
        #self._insert_center_rods(plotpart)
        # TODO: add in parametric way

        self._align_upright(plotpart)

        self.plotpart = plotpart
        return plotpart

    def get_material_usage(self):
        part = self.flatten([])
        envelope = part.layers["envelope"].polylines[0]
        area = envelope.get_area()

        return MaterialUsage().consume(self.panel.material, area)


    def get_point(self, x):
        ik = get_x_value(self.x_values, x)
        return [lst.get(ik) for lst in self.ballooned]

    def get_p1_p2(self, x, which):
        side = {"left": 0, "right": 1}[which]
        ik = get_x_value(self.x_values, x)

        p1 = self.ballooned[side].get(ik)
        p2 = self.outer_orig[side].get(ik)

        return p1, p2

    def _align_upright(self, plotpart):
        def get_p1_p2(side):
            p1 = self.get_p1_p2(getattr(self.panel.cut_front, f"x_{side}"), side)[0]
            p2 = self.get_p1_p2(getattr(self.panel.cut_back, f"x_{side}"), side)[0]

            return p2 - p1

        vector = get_p1_p2("left")
        vector += get_p1_p2("right")

        angle = vector.angle() - math.pi/2

        plotpart.rotate(-angle)
        return plotpart

    def _insert_text(self, plotpart):
        text = self.panel.name
        text_width = self.config.allowance_design * 0.8 * len(text)

        if self.config.layout_seperate_panels and not self.panel.is_lower():
            curve = self.panel.cut_back.get_curve_2d(self.cell, self.config.midribs, exact=True)
        else:
            curve = self.panel.cut_front.get_curve_2d(self.cell, self.config.midribs, exact=True).reverse()

        ik_p1 = curve.walk(0, curve.get_length()*0.15)

        p1 = curve.get(ik_p1)
        ik_p2 = curve.walk(ik_p1, text_width)
        p2 = curve.get(ik_p2)
        align = "left"

        part_text = Text(text, p1, p2,
                         align=align,
                         valign=-0.9,
                         height=0.8)
        plotpart.layers["text"] += part_text.get_vectors()

    def _insert_controlpoints(self, plotpart):
        for x in self.config.distribution_controlpoints:
            for side in ("left", "right"):
                if getattr(self.panel.cut_front, f"x_{side}") <= x <= getattr(self.panel.cut_back, f"x_{side}"):
                    p1, p2 = self.get_p1_p2(x, side)
                    plotpart.layers["L0"] += self.config.marks_laser_controlpoint(p1, p2)

    def _insert_diagonals(self, plotpart):
        def insert_diagonal(x, height, side, front):
            if height == 1:
                xval = -x
            elif height == -1:
                xval = x
            else:
                return

            if getattr(self.panel.cut_front, f"x_{side}") <= xval <= getattr(self.panel.cut_back, f"x_{side}"):
                p1, p2 = self.get_p1_p2(xval, side)
                plotpart.layers["L0"] += self.config.marks_laser_diagonal(p1, p2)
                if (front and height == -1) or (not front and height == 1):
                    plotpart.layers["marks"] += self.config.marks_diagonal_front(p1, p2)
                else:
                    plotpart.layers["marks"] += self.config.marks_diagonal_back(p1, p2)

        for strap in self.cell.straps + self.cell.diagonals:
            insert_diagonal(*strap.left_front, side="left", front=False)
            insert_diagonal(*strap.left_back, side="left", front=True)
            insert_diagonal(*strap.right_front, side="right", front=True)
            insert_diagonal(*strap.right_back, side="right", front=False)

    def _insert_attachment_points(self, plotpart, attachment_points):
        for attachment_point in attachment_points:
            if hasattr(attachment_point, "cell"):
                if attachment_point.cell != self.cell:
                    continue

                cell_pos = attachment_point.cell_pos

            elif hasattr(attachment_point, "rib"):

                if attachment_point.rib not in self.cell.ribs:
                    continue


                if attachment_point.rib == self.cell.rib1:
                    cell_pos = 0
                elif attachment_point.rib == self.cell.rib2:
                    cell_pos = 1
                else:
                    raise AttributeError
            else:
                raise AttributeError

            cut_f_l = self.panel.cut_front.x_left
            cut_f_r = self.panel.cut_front.x_right
            cut_b_l = self.panel.cut_back.x_left
            cut_b_r = self.panel.cut_back.x_right
            cut_f = cut_f_l + cell_pos * (cut_f_r - cut_f_l)
            cut_b = cut_b_l + cell_pos * (cut_b_r - cut_b_l)

            if cut_f <= attachment_point.rib_pos <= cut_b:
                rib_pos = attachment_point.rib_pos
                left, right = self.get_point(rib_pos)

                p1 = left + (right - left) * cell_pos
                d = (right - left).normalized() * 0.008 # 8mm
                if cell_pos == 1:
                    p2 = p1 + d
                else:
                    p2 = p1 - d
                    
                if cell_pos in (1, 0):
                    which = ["left", "right"][cell_pos]
                    x1, x2 = self.get_p1_p2(rib_pos, which)
                    plotpart.layers["marks"] += self.config.marks_attachment_point(x1, x2)
                    plotpart.layers["L0"] += self.config.marks_laser_attachment_point(x1, x2)
                else:
                    plotpart.layers["marks"] += self.config.marks_attachment_point(p1, p2)
                    plotpart.layers["L0"] += self.config.marks_laser_attachment_point(p1, p2)
                
                if self.config.insert_attachment_point_text:
                    text_align = "left" if cell_pos > 0.7 else "right"

                    if text_align == "right":
                        d1 = (self.get_point(cut_f_l)[0] - left).length()
                        d2 = ((self.get_point(cut_b_l)[0] - left)).length()
                    else:
                        d1 = ((self.get_point(cut_f_r)[1] - right)).length()
                        d2 = ((self.get_point(cut_b_r)[1] - right)).length()

                    bl = self.ballooned[0]
                    br = self.ballooned[1]

                    text_height = 0.01 * 0.8
                    dmin = text_height + 0.001

                    if d1 < dmin and d2 + d1 > 2*dmin:
                        offset = dmin - d1
                        ik = get_x_value(self.x_values, rib_pos)
                        left = bl.get(bl.walk(ik, offset))
                        right = br.get(br.walk(ik, offset))
                    elif d2 < dmin and d1 + d2 > 2*dmin:
                        offset = dmin - d2
                        ik = get_x_value(self.x_values, rib_pos)
                        left = bl.get(bl.walk(ik, -offset))
                        right = br.get(br.walk(ik, -offset))

                    if self.config.layout_seperate_panels and self.panel.is_lower:
                        # rotated later
                        p2 = left
                        p1 = right
                        # text_align = text_align
                    else:
                        p1 = left
                        p2 = right
                        # text_align = text_align
                    plotpart.layers["text"] += Text(" {} ".format(attachment_point.name), p1, p2,
                                                    size=0.01,  # 1cm
                                                    align=text_align, valign=0, height=0.8).get_vectors()
    
    def _insert_rigidfoils(self, plotpart):
        for rigidfoil in self.cell.rigidfoils:
            line = rigidfoil.draw_panel_marks(self.cell, self.panel)
            if line is not None:
                plotpart.layers["marks"].append(line)

                # laser dots
                plotpart.layers["L0"].append(euklid.vector.PolyLine2D([line.get(0)]))
                plotpart.layers["L0"].append(euklid.vector.PolyLine2D([line.get(len(line)-1)]))


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


class CellPlotMaker:
    run_check = True
    DefaultConf = PatternConfig
    DribPlot = DribPlot
    StrapPlot = StrapPlot
    PanelPlot = PanelPlot

    consumption: MaterialUsage

    def __init__(self, cell, attachment_points, config=None):
        self.cell = cell
        self.consumption = MaterialUsage()
        self.attachment_points = attachment_points
        self.config = self.DefaultConf(config)

        self._flattened_cell = None

    def _get_flatten_cell(self):
        if self._flattened_cell is None:
            flattened_cell = self.cell.get_flattened_cell(self.config.midribs)

            left_bal, right_bal = flattened_cell["ballooned"]

            outer_left = left_bal.offset(-self.config.allowance_general)
            outer_right = right_bal.offset(self.config.allowance_general)

            outer_orig = [outer_left, outer_right]
            outer = [l.fix_errors() for l in outer_orig]

            flattened_cell["outer"] = outer
            flattened_cell["outer_orig"] = outer_orig

            self._flattened_cell = flattened_cell

        return self._flattened_cell

    def get_panels(self, panels=None):
        cell_panels = []
        flattened_cell = self._get_flatten_cell()
        self.cell.calculate_3d_shaping(numribs=self.config.midribs)

        if panels is None:
            panels = self.cell.panels

        for panel in panels:
            plot = self.PanelPlot(panel, self.cell, flattened_cell, self.config)
            dwg = plot.flatten(self.attachment_points)
            cell_panels.append(dwg)
            self.consumption += plot.get_material_usage()
        
        return cell_panels

    def get_panels_lower(self):
        panels = [p for p in self.cell.panels if p.is_lower()]
        return self.get_panels(panels)

    def get_panels_upper(self):
        panels = [p for p in self.cell.panels if not p.is_lower()]
        return self.get_panels(panels)

    def get_dribs(self):
        diagonals = self.cell.diagonals[:]
        diagonals.sort(key=lambda d: d.name)
        dribs = []
        for drib in self.cell.diagonals[::-1]:
            drib_plot = self.DribPlot(drib, self.cell, self.config)
            dribs.append(drib_plot.flatten(self.attachment_points))
            self.consumption += drib_plot.get_material_usage()
        
        return dribs

    def get_straps(self):
        straps = self.cell.straps[:]
        straps.sort(key=lambda d: d.name)
        result = []
        for strap in straps[::-1]:
            plot = self.StrapPlot(strap, self.cell, self.config)
            result.append(plot.flatten(self.attachment_points))
            self.consumption += plot.get_material_usage()
        
        return result
    
    def get_rigidfoils(self):
        rigidfoils = []
        for rigidfoil in self.cell.rigidfoils:
            rigidfoils.append(rigidfoil.get_flattened(self.cell))
        
        return rigidfoils

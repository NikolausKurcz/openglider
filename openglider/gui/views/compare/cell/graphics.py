import logging

import pandas
import euklid
from openglider.utils import sign
from openglider.utils.colors import Color
from openglider.glider.project import GliderProject
from openglider.gui.views_2d.canvas import LayoutGraphics
from openglider.gui.views.compare.cell.settings import CellPlotLayers
from openglider.vector.drawing import Layout, PlotPart


logger = logging.getLogger(__name__)


class GliderCellPlots:
    project: GliderProject
    config: CellPlotLayers
    color: Color
    cache: dict[int, pandas.DataFrame]

    def __init__(self, project: GliderProject, color: Color) -> None:
        self.project = project
        self.color = color
        self.cache = {}
        self.config = CellPlotLayers()
        
    def get(self, cell_no: int, config: CellPlotLayers) -> LayoutGraphics:
        if config != self.config:
            self.cache = {}
            self.config = config.copy()

        if cell_no not in self.cache:
            glider = self.project.get_glider_3d()

            zero_line = euklid.vector.PolyLine2D([
                [0,0], [1,0]
            ])
            if cell_no < len(glider.cells):
                cell = glider.cells[cell_no]
                ballooning_max = max([-sign(p[0]) * p[1] for p in cell.ballooning_modified])
                ballooning_min = min([-sign(p[0]) * p[1] for p in cell.ballooning_modified])

                # get entry x values
                panels = cell.get_connected_panels()
                cuts = set()
                for p in panels:
                    x1 = max([p.cut_front.x_left, p.cut_front.x_right])
                    x2 = min([p.cut_back.x_left, p.cut_back.x_right])

                    for panel_cut in (x1, x2):
                        if abs(panel_cut) < (1 - 1e-10):
                            cuts.add(panel_cut)

                cut_lines = []
                for cut in cuts:
                    x = abs(float(cut))

                    y = ballooning_max
                    if cut > 0:
                        y = ballooning_min
                    
                    cut_lines.append(euklid.vector.PolyLine2D([
                        [x, 0],
                        [x, y]
                    ]))

                part = PlotPart([cell.ballooning_modified.draw()] + cut_lines, marks=[zero_line])
                dwg = Layout([part])
                dwg.layer_config["cuts"] = {
                    "id": 'outer',
                    "stroke-width": "0.25",
                    "stroke": "red",
                    "stroke-color": f"#{self.color.hex()}",
                    "fill": "none"
                    }
                self.cache[cell_no] = dwg
            
            else:
                self.cache[cell_no] = Layout()
        
        return LayoutGraphics(self.cache[cell_no])


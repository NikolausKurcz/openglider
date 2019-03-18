import os
import subprocess

from openglider import jsonify

import openglider.plots.spreadsheets
import openglider.plots.cuts
from openglider.plots.drawing import PlotPart, Layout
from openglider.plots.glider import PlotMaker
import openglider.plots.marks
#import openglider.plots.sketches


class Patterns(object):
    class DefaultConf(PlotMaker.DefaultConfig):
        pass

    def __init__(self, glider2d, config=None):
        self.glider_2d = glider2d
        self.config = self.DefaultConf(config)

    def __json__(self):
        return {
            "glider2d": self.glider_2d,
            "config": self.config
        }

    def _get_sketches(self, outdir, glider=None):
        print("create sketches")
        glider = glider or self.glider_2d.get_glider_3d()
        import openglider.plots.sketches as sketch
        shapeplot = sketch.ShapePlot(self.glider_2d, glider)
        design_upper = shapeplot.copy().insert_design(lower=True)
        design_upper.insert_cell_names()
        design_lower = shapeplot.copy().insert_design(lower=False)

        lineplan = shapeplot.copy()
        lineplan.insert_design(lower=True)
        lineplan.insert_attachment_points()
        lineplan.insert_rib_numbers()

        diagonals = sketch.ShapePlot(self.glider_2d, glider)
        diagonals.insert_cells()
        diagonals.insert_attachment_points(add_text=False)
        diagonals.insert_diagonals()

        straps = sketch.ShapePlot(self.glider_2d, glider)
        straps.insert_cells()
        straps.insert_attachment_points(add_text=False)
        straps.insert_straps()

        drawings = [design_upper.drawing, design_lower.drawing, lineplan.drawing, diagonals.drawing, straps.drawing]

        return drawings

    def unwrap(self, outdir, glider=None):
        def fn(filename):
            return os.path.join(outdir, filename)

        subprocess.call("mkdir -p {}".format(outdir), shell=True)

        if self.config.profile_numpoints:
            self.glider_2d.num_profile = self.config.profile_numpoints

        glider = glider or self.glider_2d.get_glider_3d()

        drawings = self._get_sketches(outdir, glider)

        if self.config.complete_glider:
            glider_complete = glider.copy_complete()
            glider_complete.rename_parts()
            plots = PlotMaker(glider_complete, config=self.config)
            glider_complete.lineset.iterate_target_length()
        else:
            plots = PlotMaker(glider, config=self.config)
            glider.lineset.iterate_target_length()
            
        plots.unwrap()
        all_patterns = plots.get_all_grouped()

        # with open(fn("patterns.json"), "w") as outfile:
        #     jsonify.dump(plots, outfile)

        designs = Layout.stack_column(drawings, self.config.patterns_align_dist_y)
        all_patterns.append_left(designs, distance=self.config.patterns_align_dist_x*2)

        print("export patterns")

        all_patterns.scale(1000)
        all_patterns.export_svg(fn("plots_all.svg"))
        all_patterns.export_dxf(fn("plots_all_dxf2000.dxf"))
        all_patterns.export_dxf(fn("plots_all_dxf2007.dxf"), "AC1021")
        all_patterns.export_ntv(fn("plots_all.ntv"))



        # ribs = packer.pack_parts(parts["ribs"].parts, sheet_size=sheet_size)
        # panels = packer.pack_parts(parts["panels"].parts, sheet_size=sheet_size)

        # for sheet_no, sheet in enumerate(ribs):
        #     openglider.plots.create_svg(sheet, fn("ribs_{}".format(sheet_no)))
        # for sheet_no, sheet in enumerate(panels):
        #     openglider.plots.create_svg(sheet, fn("panels_{}".format(sheet_no)))

        # sketches = openglider.plots.sketches.get_all_plots(self.glider_2d, glider)
        #
        # for sketch_name in ("design_upper", "design_lower"):
        #     sketch = sketches.pop(sketch_name)
        #     sketch.drawing.scale_a4()
        #     sketch.drawing.export_svg(fn(sketch_name+".svg"), add_styles=True)
        #
        # for sketch_name, sketch in sketches.items():
        #     sketch.drawing.scale_a4()
        #     sketch.drawing.export_svg(fn(sketch_name+".svg"), add_styles=False)

        print("output spreadsheets")
        excel = openglider.plots.spreadsheets.get_glider_data(glider)
        excel.saveas(os.path.join(outdir, "data.ods"))

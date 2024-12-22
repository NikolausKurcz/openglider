from openglider.glider.project import GliderProject
from openglider.plots.sketches.shapeplot import ShapePlot
from openglider.plots.sketches.lineplan import LinePlan
from openglider.glider.shape import Shape


def get_all_plots(project: GliderProject, shapes: tuple[Shape, Shape]) -> dict[str, ShapePlot]:
    design_upper = ShapePlot(project)
    design_upper.draw_design(shapes, lower=False)
    design_upper.draw_design(shapes, lower=False, left=True)

    design_lower = ShapePlot(project)
    design_lower.draw_design(shapes, lower=True)
    design_lower.draw_design(shapes, lower=True, left=True)
    design_lower.draw_cells(shapes)
    design_lower.draw_cells(shapes, left=True)

    lineplan = LinePlan(project)  #.draw_shape().draw_attachment_points()
    lineplan.draw_cells(shapes)
    lineplan.draw_cells(shapes, left=True)
    lineplan.draw_attachment_points(shapes, add_text=False)
    lineplan.draw_attachment_points(shapes, add_text=False, left=True)
    lineplan.draw_lines(shapes, add_text=True)

    base_shape = ShapePlot(project)
    base_shape.draw_cells(shapes)
    base_shape.draw_cells(shapes, left=True)
    base_shape.draw_design(shapes, lower=True)
    base_shape.draw_design(shapes, lower=True, left=True)

    straps = base_shape.copy()
    straps.draw_straps(shapes)
    straps.draw_straps(shapes, left=True)

    diagonals = base_shape.copy()
    diagonals.draw_diagonals(shapes)
    diagonals.draw_diagonals(shapes, left=True)


    return {
        "design_upper": design_upper,
        "design_lower": design_lower,
        "lineplan": lineplan,
        "straps": straps,
        "diagonals": diagonals
    }
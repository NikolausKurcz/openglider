from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import euklid
import pyfoil

from openglider.mesh import Mesh
from openglider.utils.cache import cached_function
from openglider.utils.dataclass import BaseModel
from openglider.vector.drawing import PlotPart
from openglider.vector.polygon import Ellipse
from openglider.vector.unit import Angle, Length, Percentage
from pydantic import ConfigDict

if TYPE_CHECKING:
    from openglider.glider.rib.rib import Rib

logger = logging.getLogger(__name__)


class RibHoleBase(BaseModel):
    name: str = "unnamed"
    margin: Percentage | Length= Percentage("2%")

    @cached_function('margin')
    def get_envelope_airfoil(self, rib: Rib) -> pyfoil.Airfoil:
        return rib.get_offset_outline(self.margin)
    
    @cached_function("margin")
    def get_envelope_boundaries(self, rib: Rib) -> tuple[Percentage, Percentage]:
        envelope = self.get_envelope_airfoil(rib)
        x2 = envelope.curve.nodes[0][0]
        x1 = min([p[0] for p in envelope.curve.nodes])

        return Percentage(x1), Percentage(x2)
    
    def align_contolpoints(self, controlpoints: list[euklid.vector.Vector2D], rib: Rib) -> list[euklid.vector.Vector2D]:
        envelope = self.get_envelope_airfoil(rib)
        return [envelope.align(cp) for cp in controlpoints]

    def _get_curves(self, rib: Rib, num: int) -> list[euklid.vector.PolyLine2D]:
        raise NotImplementedError()
    
    def get_curves(self, rib: Rib, num: int=80, scale: bool=False) -> list[euklid.vector.PolyLine2D]:
        curves = self._get_curves(rib, num)

        if scale:
            return [line.scale(rib.chord) for line in curves]
        else:
            return curves

    def get_centers(self, rib: Rib, scale: bool=False) -> list[euklid.vector.Vector2D]:
        raise NotImplementedError()
    
    def get_3d(self, rib: Rib, num: int=20) -> list[euklid.vector.PolyLine3D]:
        hole = self.get_curves(rib, num=num)
        return [rib.align_all(c) for c in hole]

    def get_flattened(self, rib: Rib, num: int=80, layer_name: str="cuts") -> PlotPart:
        curves = [line.scale(rib.chord) for line in self.get_curves(rib, num)]
        
        pp = PlotPart()
        pp.layers[layer_name] += curves
        return pp
    
    def get_parts(self, rib: Rib) -> list[PlotPart]:
        return []
    
    def get_mesh(self, rib: Rib) -> Mesh | None:
        return None


class RibHole(RibHoleBase):
    """
    Round holes.
    height is relative to profile height, rotation is from lower point
    """
    pos: Percentage
    size: Percentage=Percentage(0.5)
    width: Percentage=Percentage(1.)

    vertical_shift: Percentage=Percentage(0)
    rotation: Angle=Angle(0)

    def _get_points(self, rib: Rib) -> tuple[euklid.vector.Vector2D, euklid.vector.Vector2D]:
        lower = rib.profile_2d.get(self.pos.si)
        upper = rib.profile_2d.get(-self.pos.si)

        diff = upper - lower
        if self.rotation:
            diff = euklid.vector.Rotation2D(self.rotation.si).apply(diff)

        center = lower + diff * (0.5 + self.vertical_shift.si/2)
        outer_point = center + diff.normalized() * self.get_diameter(rib)/2

        return center, outer_point

    def _get_curves(self, rib: Rib, num: int=80) -> list[euklid.vector.PolyLine2D]:
        center, outer_point = self._get_points(rib)
        
        circle = Ellipse.from_center_p2(center, outer_point, self.width.si)

        return [circle.get_sequence(num)]
    
    def get_diameter(self, rib: Rib) -> float:
        lower = rib.profile_2d.get(self.pos.si)
        upper = rib.profile_2d.get(-self.pos.si)

        diff = upper - lower
        
        return diff.length() * self.size.si
    
    def get_centers(self, rib: Rib, scale: bool=False) -> list[euklid.vector.Vector2D]:
        return [self._get_points(rib)[0]]


def polygon(points: list[euklid.vector.Vector2D], corner_size: float, num_points) -> euklid.vector.PolyLine2D:
    segments = []

    def get_point(index: int) -> euklid.vector.Vector2D:
        if index >= len(points):
            index -= len(points)
        
        return points[index]

    for i in range(len(points)):
        p1 = get_point(i)
        p2 = get_point(i+1)
        p3 = get_point(i+2)

        segments.append([
            p1 + (p2-p1) * (1-corner_size/2),
            p2,
            p2 + (p3-p2) * (corner_size/2)
        ])

    sequence = []
    for i, segment in enumerate(segments):
        sequence += euklid.spline.BSplineCurve(segment).get_sequence(num_points).nodes

        if corner_size < 1:
            if i+1 >= len(segments):
                segment2 = segments[0]
            else:
                segment2 = segments[i+1]
            
            sequence += [segment[-1], segment2[0]]

    return euklid.vector.PolyLine2D(sequence).resample(num_points)


class PolygonHole(RibHoleBase):
    points: list[euklid.vector.Vector2D]
    corner_size: float=1
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_centers(self, rib: Rib, scale: bool=False) -> list[euklid.vector.Vector2D]:
        centers = [sum(self.points, start=euklid.vector.Vector2D())/len(self.points)]

        if scale:
            return [p * rib.chord for p in centers]
        
        return centers

    def _get_curves(self, rib: Rib, num: int=160) -> list[euklid.vector.PolyLine2D]:
        return [polygon(self.points, self.corner_size, num)]


class RibSquareHole(RibHoleBase):
    x: Percentage
    width: Percentage | Length
    height: Percentage
    corner_size: float = 1

    def get_centers(self, rib: Rib, scale: bool=False) -> list[euklid.vector.Vector2D]:
        width = rib.convert_to_percentage(self.width)

        x1 = self.x - width/2
        x2 = self.x + width/2

        xmin, xmax = self.get_envelope_boundaries(rib)
        if x1 < xmin or x2 > xmax:
            return []
        
        centers = [rib.profile_2d.align([self.x, 0])]
        
        if scale:
            return [p * rib.chord for p in centers]
        
        return centers
    
    def _get_curves(self, rib: Rib, num: int=80) -> list[euklid.vector.PolyLine2D]:
        width = rib.convert_to_percentage(self.width)
        x1 = self.x - width/2
        x2 = self.x + width/2

        xmin, xmax = self.get_envelope_boundaries(rib)
        if x1 < xmin or x2 > xmax:
            return []
        
        p1, p2, p3, p4 = self.align_contolpoints([
            euklid.vector.Vector2D([x1, -self.height]),
            euklid.vector.Vector2D([x2, -self.height]),
            euklid.vector.Vector2D([x2, self.height]),
            euklid.vector.Vector2D([x1, self.height])
        ], rib)

        return PolygonHole(points=[p1, p2, p3, p4]).get_curves(rib, num)


class MultiSquareHole(RibHoleBase):
    start: Percentage
    end: Percentage
    height: Percentage
    num_holes: int
    border_width: Percentage | Length

    @property
    def total_border(self) -> Percentage | Length:
        return (self.num_holes-1) * self.border_width

    def hole_width(self, rib: Rib) -> Percentage:
        total_border = rib.convert_to_percentage(self.total_border)

        width = (self.end - self.start - total_border) / self.num_holes
        if width < 1e-5:
            raise ValueError(f"Cannot fit {self.num_holes} with border: {self.border_width}")

        return width
    
    def hole_x_values(self, rib: Rib) -> list[Percentage]:
        hole_width = self.hole_width(rib)
        border_width = rib.convert_to_percentage(self.border_width)

        x = self.start + hole_width/2

        return [x + i*(hole_width+border_width) for i in range(self.num_holes)]
    
    def _get_holes(self, rib: Rib) -> list[RibSquareHole]:
        hole_width = self.hole_width(rib)
        holes = []
        for center in self.hole_x_values(rib):
            holes.append(RibSquareHole(x=center, width=hole_width, height=self.height, margin=self.margin))

        return holes
    
    def get_centers(self, rib: Rib, scale: bool=False) -> list[euklid.vector.Vector2D]:
        holes = []
        for hole in self._get_holes(rib):
            holes += hole.get_centers(rib, scale=scale)
        
        return holes
    
    def _get_curves(self, rib: Rib, num: int=80) -> list[euklid.vector.PolyLine2D]:
        curves = []
        for hole in self._get_holes(rib):
            curves += hole.get_curves(rib, num)
        
        return curves


class AttachmentPointHole(RibHoleBase):
    start: Percentage
    end: Percentage
    num_holes: int
    border: Length | Percentage=Length("4cm")
    border_side: Length | Percentage=Length("4cm")
    border_diagonal: Length | Percentage = Length(0)

    border_top: Length | Percentage | None = None

    corner_size: Percentage = Percentage(1.)
    top_triangle_factor: Percentage | None = None

    min_hole_height: Length = Length("2cm")

    def fit_holes(
            self,
            hole_positions: list[tuple[Percentage, Percentage]],
            upper: euklid.vector.Interpolation,
            lower: euklid.vector.Interpolation,
            triangle_factors: tuple[Percentage | None, Percentage | None] = (None, None)
            ) -> list[PolygonHole]:
        holes = []

        start = min([p[0] for p in upper.nodes + lower.nodes])
        end = max([p[0] for p in upper.nodes + lower.nodes])

        # todo: find measure
        def get_nodes(x: Percentage, triangle_factor: Percentage | None) -> list[euklid.vector.Vector2D]:
            x_normalized = max(start, min(end, x.si))
            upper_y = upper.get_value(x_normalized)
            lower_y = lower.get_value(x_normalized)

            if triangle_factor is not None:
                lower_y = lower_y + (upper_y - lower_y) * triangle_factor.si
            
            if abs(upper_y - lower_y) < self.min_hole_height:
                return [
                    euklid.vector.Vector2D([x_normalized, (upper_y+lower_y)/2])
                ]
            else:
                return [
                    euklid.vector.Vector2D([x_normalized, upper_y]),
                    euklid.vector.Vector2D([x_normalized, lower_y])
                ]

        for hole_start, hole_end in hole_positions:
            if hole_end < start or hole_start > end:
                continue
            points = get_nodes(hole_start, triangle_factors[0]) + get_nodes(hole_end, triangle_factors[1])[::-1]

            if len(points) > 2:
                holes.append(PolygonHole(points=points, corner_size=self.corner_size.si))

        return holes


    @cached_function('self')
    def _get_holes_bottom(self, rib: Rib) -> list[PolygonHole]:
        envelope = self.get_envelope_airfoil(rib)
        lower_envelope = envelope.curve.get(envelope.noseindex, len(envelope.curve.nodes))
        lower_interpolation = euklid.vector.Interpolation(lower_envelope.nodes)

        diagonal_border = rib.convert_to_percentage(self.border_diagonal).si
        side_border_pct = rib.convert_to_percentage(self.border_side)

        upper_1 = rib.profile_2d.align([self.start, -1])
        upper_2 = rib.profile_2d.align([(self.start+self.end)/2, 1])
        upper_3 = rib.profile_2d.align([self.end, -1])

        start_ik = envelope.get_ik(self.start) - envelope.noseindex
        end_ik = envelope.get_ik(self.end) - envelope.noseindex

        upper_with_border = euklid.vector.PolyLine2D([upper_1, upper_2, upper_3]).offset(diagonal_border)
        cut_front = lower_envelope.cut(upper_with_border.nodes[0], upper_with_border.nodes[1], start_ik)
        cut_end = lower_envelope.cut(upper_with_border.nodes[1], upper_with_border.nodes[2], end_ik)

        lower = euklid.vector.Interpolation(lower_envelope.get(cut_front[0], cut_end[0]).nodes)
        upper = euklid.vector.Interpolation(upper_with_border.get(cut_front[1], 1+cut_end[1]).nodes)

        border_pct = rib.convert_to_percentage(self.border)

        total_border_pct = (2*side_border_pct + (self.num_holes-1)*border_pct)

        start = Percentage(lower.nodes[0][0])
        end = Percentage(lower.nodes[-1][0])

        hole_width  = ((self.end - self.start) - total_border_pct)/self.num_holes

        if hole_width < 0:
            raise ValueError(f"not enough space for {self.num_holes} holes between {self.start} / {self.end} ({rib.name})")

        holes = []

        for hole_no in range(self.num_holes):
            hole_left = self.start + side_border_pct + hole_no*border_pct + hole_no*hole_width
            hole_right = hole_left + hole_width

            holes.append((
                max(hole_left, start),
                min(hole_right, end)
            ))

        
        return self.fit_holes(holes, upper, lower)
    
    @cached_function('self')
    def _get_holes_top(self, rib: Rib) -> list[PolygonHole]:
        if self.border_top is None:
            return []
        
        envelope = self.get_envelope_airfoil(rib)
        diagonal_border = rib.convert_to_percentage(self.border_diagonal).si
        side_border_pct = rib.convert_to_percentage(self.border_side)

        upper_curve = euklid.vector.PolyLine2D(envelope.curve.nodes[:envelope.noseindex][::-1])

        top_center = rib.profile_2d.align([(self.start+self.end)/2, 1])
        bottom_start = rib.profile_2d.align([self.start, -1])
        bottom_end = rib.profile_2d.align([self.end, -1])

        def get_ik_x(polyline: euklid.vector.PolyLine2D, x: float) -> float:
            return polyline.cut(
                euklid.vector.Vector2D([x, 0.]),
                euklid.vector.Vector2D([x, 1.])
            )[0][0]

        diagonal_with_border = euklid.vector.PolyLine2D([bottom_start, top_center, bottom_end]).offset(-diagonal_border)
        nearest_top_x = diagonal_with_border.nodes[1][0]
        nearest_top_ik = get_ik_x(upper_curve, nearest_top_x)

        cut_1_front = get_ik_x(upper_curve, self.start.si)
        cut_1_back: tuple[float, float] = upper_curve.cut(diagonal_with_border.nodes[0], diagonal_with_border.nodes[1], nearest_top_ik)
        cut_2_front: tuple[float, float] = upper_curve.cut(diagonal_with_border.nodes[1], diagonal_with_border.nodes[2], nearest_top_ik)
        cut_2_back = get_ik_x(upper_curve, self.end.si)

        diagonal_cut_front = get_ik_x(diagonal_with_border, self.start.si)
        diagonal_cut_back = get_ik_x(diagonal_with_border, self.end.si)

        upper_interpolation_front = euklid.vector.Interpolation(
            upper_curve.get(
                cut_1_front,
                cut_1_back[0]
            ).nodes)

        upper_interpolation_back = euklid.vector.Interpolation(
            upper_curve.get(
                cut_2_front[0],
                cut_2_back
            ).nodes
        )

        diagonal_interpolation_front = euklid.vector.Interpolation(
            diagonal_with_border.get(
                diagonal_cut_front,
                cut_1_back[1]
            ).nodes
        )
        diagonal_interpolation_back = euklid.vector.Interpolation(
            diagonal_with_border.get(
                cut_2_front[1]+1,
                diagonal_cut_back
            ).nodes
        )

        side_border_pct = rib.convert_to_percentage(self.border_side)
        border_pct = rib.convert_to_percentage(self.border_top)

        total_border_pct = (2*side_border_pct + (self.num_holes-1)*border_pct)

        hole_width  = (Percentage(float(abs(self.start-self.end))) - total_border_pct)/self.num_holes

        if hole_width < 0:
            raise ValueError(f"not enough space for {self.num_holes} holes between {self.start} / {self.end} ({rib.name})")

        hole_positions = []

        for hole_no in range(self.num_holes):
            left = self.start + side_border_pct + hole_no*border_pct + hole_no*hole_width
            right = left + hole_width

            hole_positions.append((left, right))

        holes = self.fit_holes(hole_positions, upper_interpolation_front, diagonal_interpolation_front, (None, self.top_triangle_factor))
        holes += self.fit_holes(hole_positions, upper_interpolation_back, diagonal_interpolation_back, (self.top_triangle_factor, None))

        return holes

    def _get_curves(self, rib: Rib, num: int=80) -> list[euklid.vector.PolyLine2D]:
        curves = []
        for hole in self._get_holes_bottom(rib):
            curves += hole.get_curves(rib, num)
        for hole in self._get_holes_top(rib):
            curves += hole.get_curves(rib, num)

        return curves

    def get_centers(self, rib: Rib, scale: bool=False) -> list[euklid.vector.Vector2D]:
        holes = []
        for hole in self._get_holes_bottom(rib):
            holes += hole.get_centers(rib, scale=scale)
        for hole in self._get_holes_top(rib):
            holes += hole.get_centers(rib, scale=scale)

        return holes
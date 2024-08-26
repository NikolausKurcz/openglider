from __future__ import annotations

from typing import TYPE_CHECKING, Any
import logging
import math

import pydantic
import euklid

from openglider.lines.node import Node
from openglider.lines import line_types
from openglider.utils.cache import cached_property
from openglider.mesh import Mesh, Vertex, Polygon
from openglider.utils.dataclass import BaseModel
from openglider.vector.unit import Length

if TYPE_CHECKING:
    from openglider.glider.glider import Glider
    from openglider.glider.rib.rib import Rib

logger = logging.getLogger(__name__)


class Line(BaseModel):
    lower_node: Node
    upper_node: Node

    target_length: Length | None

    v_inf: euklid.vector.Vector3D

    line_type: line_types.LineType = line_types.LineType.get("default")
    color: str = "default"
    name: str = ""

    force: float | None = None
    trim_correction: Length | None = None
    init_length: Length | None = None

    # sag angle
    sag_par_1: float | None = None
    # sag offset from initial knot
    sag_par_2: float | None = None
    rho_air: float = 1.2

    def model_post_init(self, __context: Any) -> None:
        if self.init_length is None:
            self.init_length = self.target_length

    #@property
    #def color(self) -> str:
    #    return self._color or "default"

    #@color.setter
    #def color(self, color: str) -> None:
    #    if color in self.line_type.colors:
    #        self._color = color

    @property
    def has_geo(self) -> bool:
        """
        true if upper and lower nodes of the line were already computed
        """
        #the node vectors can be None or numpy.arrays. So we have to check for both types
        try:
            return (self.lower_node.position.length() + self.upper_node.position.length()) > 0
        except TypeError:
            # one of the nodes vec is None
            return False

    @property
    def v_inf_0(self) -> euklid.vector.Vector3D:
        return self.v_inf.normalized()

    #@cached_property('lower_node.position', 'upper_node.position')
    @property
    def diff_vector(self) -> euklid.vector.Vector3D:
        """
        Line Direction vector (normalized)
        :return:
        """
        return (self.upper_node.position - self.lower_node.position).normalized()

    #@cached_property('lower_node.position', 'upper_node.position')
    @property
    def diff_vector_projected(self) -> euklid.vector.Vector3D:
        return (self.upper_node.vec_proj - self.lower_node.vec_proj).normalized()

    @cached_property('lower_node.vec_proj', 'upper_node.vec_proj')
    def length_projected(self) -> float:
        return (self.lower_node.vec_proj - self.upper_node.vec_proj).length()

    @property
    def length_no_sag(self) -> float:
        return (self.upper_node.position - self.lower_node.position).length()
    
    @cached_property('lower_node.position', 'upper_node.position', 'v_inf', 'sag_par_1', 'sag_par_2')
    def length_with_sag(self) -> float:
        assert self.sag_par_1 is not None

        alpha = math.asin(self.diff_vector.normalized().dot(self.v_inf_0))
        q1 = self.ortho_pressure / self.force_projected / 2
        q2 = self.sag_par_1 + math.tan(alpha)

        if q1 < 1e-10:
            # simplified integral: y = q2 * x -> length = sqrt(1+q2) * length_projected
            return math.sqrt(1+q2**2) * self.length_projected
        
        def get_integral(dx: float) -> float:
            # y = - q1 x² + q2 x + d , dy/dx = -2 q1 x + q2
            # integral sqrt(1 + (-2 q1 x + q2)^2)dx = (sqrt((q2 - 2*q1*x)^2 + 1) (q2 - 2 q1 x) + sinh^(-1)(q2 - 2 q1 x))/(4 q1) + constant
            upper = math.sqrt((q2-2*q1*dx)**2+1) * (q2-2*q1*dx) + (math.asinh(q2 - 2*q1*dx))
            lower = 4*q1

            return -(upper / lower)
        
        return get_integral(self.length_projected) - get_integral(0)

    def get_stretched_length(self, pre_load: float=50, sag: bool=True) -> float:
        """
        Get the total line-length for production using a given stretch
        length = len_0 * (1 + stretch*force)
        """
        if sag:
            l_0 = self.length_with_sag
        else:
            l_0 = self.length_no_sag
        factor = self.line_type.get_stretch_factor(pre_load) / self.line_type.get_stretch_factor(self.force or 0)
        return l_0 * factor

    #@cached_property('v_inf', 'type.cw', 'type.thickness')
    @property
    def ortho_pressure(self) -> float:
        """
        drag per meter (projected)
        :return: 1/2 * cw * d * v^2
        """
        return 1 / 2 * self.line_type.cw * self.line_type.thickness * self.rho_air * self.v_inf.dot(self.v_inf)

    #@cached_property('lower_node.position', 'upper_node.position', 'v_inf')
    @property
    def drag_total(self) -> float:
        """
        Get total drag of line
        :return: 1/2 * cw * A * v^2
        """
        drag = self.ortho_pressure * self.length_projected
        return drag

    def get_weight(self) -> float:
        if self.line_type.weight is None:
            logger.warning("predicting weight of linetype {self.line_type.name} by line-thickness.")
            logger.warning("Please enter line_weight in openglider/lines/line_types")
            weight = self.line_type.predict_weight()
        else:
            weight = self.line_type.weight
        try:
            return weight * self.length_with_sag
        except ValueError:
            # computing weight without sag
            return weight * self.length_no_sag

    @cached_property('force', 'lower_node.vec_proj', 'lower_node.position', 'upper_node.vec_proj', 'upper_node.position')
    def force_projected(self) -> float:
        try:
            return self.force * self.length_projected / self.length_no_sag
        except Exception as e:
            logger.error(f"invalid force: {self.name}, {self.force} {self.length_no_sag}")
            raise e

    def get_line_points(self, sag: bool=True, numpoints: int=10) -> list[euklid.vector.Vector3D]:
        """
        Return points of the line
        """
        if self.sag_par_1 is None or self.sag_par_2 is None:
            sag=False
        return [self.get_line_point(i / (numpoints - 1), sag=sag) for i in range(numpoints)]

    def get_line_point(self, x: float, sag: bool=True) -> euklid.vector.Vector3D:
        """pos(x) [x,y,z], x: [0,1]"""
        point = self.lower_node.position * (1. - x) + self.upper_node.position * x
        if sag:
            return point + self.v_inf_0 * self.get_sag(x)

        return point

    def get_sag(self, x: float) -> float:
        """sag u(x) [m], x: [0,1]"""
        xi = x * self.length_projected
        u = (- xi ** 2 / 2 * self.ortho_pressure /
             self.force_projected + xi *
             self.sag_par_1 + self.sag_par_2)
        return float(u)

    def get_mesh(self, numpoints: int=2, segment_length: float | None=None) -> Mesh:
        if segment_length is not None:
            numpoints = max(round(self.length_no_sag / segment_length), 2)

        line_points = [Vertex(*point) for point in self.get_line_points(numpoints=numpoints)]
        boundary: dict[str, list[Vertex]] = {"lines": []}
        if self.lower_node.node_type == Node.NODE_TYPE.LOWER:
            boundary["lower_attachment_points"] = [line_points[0]]
        else:
            boundary["lines"].append(line_points[0])
        if self.upper_node.node_type == Node.NODE_TYPE.UPPER:
            boundary["attachment_points"] = [line_points[-1]]
        else:
            boundary["lines"].append(line_points[-1])
        
        spring = self.line_type.get_spring_constant()
        stretch_factor = 1 + (self.force or 0) / spring
        attributes = {
            "name": self.name,
            "l_12": self.length_no_sag / stretch_factor / (numpoints-1),
            "e_module": spring,
            "e_module_push": 0,
            "density": max(0.0001, (self.line_type.weight or 0)/1000)  # g/m -> kg/m, min: 0,1g/m
        }

        if color := self.line_type.colors.get(self.color, None):
            poly_name = f"lines_#{color.hex()}"
        else:
            poly_name = "lines"

        line_poly = {
            poly_name: [
                Polygon(line_points[i:i + 2], attributes=attributes)
                for i in range(len(line_points) - 1)
                ]}

        return Mesh(line_poly, boundary)

    @property
    def _get_projected_par(self) -> list[float | None]:
        if self.sag_par_1 is None or self.sag_par_2 is None:
            raise ValueError(f"No sag calculated: {self.name}")
        c1_n = self.lower_node.get_diff().dot(self.v_inf_0)
        c2_n = self.upper_node.get_diff().dot(self.v_inf_0)
        return [c1_n + self.sag_par_1, c2_n / self.length_projected + self.sag_par_2]

    def get_connected_ribs(self, glider: Glider) -> list[Rib]:
        '''
        return the connected ribs
        '''
        ribs = []
        att_pnts = glider.lineset.get_upper_influence_nodes(self)
        for rib in glider.ribs:
            if any(p in rib.attachment_points for p in att_pnts):
                ribs.append(rib)
        
        return ribs

    def get_rib_normal(self, glider: Glider) -> euklid.vector.Vector3D:
        '''
        return the rib normal of the connected rib(s)
        '''
        ribs = self.get_connected_ribs(glider)
        result = euklid.vector.Vector3D()

        for rib in ribs:
            result += rib.normalized_normale

        return result.normalized()

    def rib_line_norm(self, glider: Glider) -> float:
        '''
        returns the squared norm of the cross-product of
        the line direction and the normal-direction of
        the connected rib(s)
        '''
        return self.diff_vector.dot(self.get_rib_normal(glider))

    def get_correction_influence(self, residual_force: euklid.vector.Vector3D) -> float:
        '''
        returns an influence factor [force / length] which is a proposal for
        the correction of a residual force if the line is moved in the direction
        of the residual force
        '''
        if self.force is None:
            raise ValueError()
        diff = self.diff_vector
        l = diff.length()
        r = residual_force.length()
        
        normed_residual_force = residual_force / r
        normed_diff_vector = diff / l
        f = 1. - normed_residual_force.dot(normed_diff_vector)   # 1 if normal, 0 if parallel
        return f * self.force / l

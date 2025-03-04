from __future__ import annotations
import math
import euklid

from openglider.airfoil import Profile3D
from openglider.utils.cache import cached_property
from openglider.utils.dataclass import BaseModel


class BasicCell(BaseModel):
    """
    A very simple cell without any extras like midribs, diagonals,..
    """
    prof1: Profile3D
    prof2: Profile3D
    ballooning_phi: list[float]
    name: str = "unnamed_cell"

    def point_basic_cell(self, y: int=0, ik: float=0) -> euklid.vector.Vector3D:
        ##round ballooning
        return self.midrib(y).get(ik)

    def midrib(self, y_value: float, ballooning: bool=True, arc_argument: bool=True, close_trailing_edge: bool=False) -> Profile3D:
        if y_value <= 0:              # left side
            return self.prof1
        elif y_value >= 1:            # right side
            return self.prof2
        else:                   # somewhere else

            # Ballooning is considered to be arcs, following 2 (two!) simple rules:
            # 1: x1 = x*d
            # 2: x2 = R*normvekt*(cos(phi2)-cos(phi)
            # 3: norm(d)/r*(1-x) = 2*sin(phi(2))

            x_values: list[float] = []
            distances = []
            heights = []
            node_len = len(self.prof1.curve)

            diff = self.prof2.curve.sub(self.prof1.curve)

            if not ballooning:
                midrib = self.prof1.curve.add(diff * y_value)
            
            else:
                for i in range(len(self.prof1.curve.nodes)):  # Arc -> phi(bal) -> r  # oder so...
                    x_left = self.prof1.x_values[i]
                    x_right = self.prof2.x_values[i]
                    x_values.append(x_left + y_value * (x_right - x_left))
                    ballooning_radius = self.ballooning_radius[i]

                    if close_trailing_edge and i in (0, node_len-1):
                        d = y_value
                        h = 0.

                    elif ballooning_radius > 1e-10:
                        phi = self.ballooning_phi[i]    # phi is half only the half
                        
                        if arc_argument:
                            psi = phi * 2 * y_value         # psi [-phi:phi]
                            d = 0.5 - 0.5 * math.sin(phi - psi) / math.sin(phi)
                            h = (math.cos(phi - psi) - math.cos(phi)) * ballooning_radius
                        else:
                            d = y_value
                            h = (math.cos(math.asin((2 * d - 1) * math.sin(phi))) -  math.cos(phi)) * ballooning_radius
                    else:  # Without ballooning
                        d = y_value
                        h = 0.
                    
                    distances.append(d)
                    heights.append(h)
            
                midrib = self.prof1.curve.add(diff.scale_nodes(distances)).add(self.normvectors.scale_nodes(heights))

            return Profile3D(curve=midrib, x_values=x_values)

    @cached_property('prof1', 'prof2')
    def normvectors(self) -> euklid.vector.PolyLine3D:
        prof1 = self.prof1.curve
        prof2 = self.prof2.curve
        
        t_1 = self.prof1.tangents
        t_2 = self.prof2.tangents
        # cross (differenzvektor, tangentialvektor)

        normals = []

        for p1, p2, t1, t2 in zip(prof1, prof2, t_1, t_2):
            normal = (t1 + t2).cross(p1 - p2).normalized()
            normals.append(normal)
        
        return euklid.vector.PolyLine3D(normals)

    @cached_property('ballooning_phi', 'prof1', 'prof2')
    def ballooning_radius(self) -> list[float]:
        prof1 = self.prof1.curve.nodes
        prof2 = self.prof2.curve.nodes

        radius: list[float] = []

        for p1, p2, phi in zip(prof1, prof2, self.ballooning_phi):
            if phi < 1e-10:
                radius.append(0.)
            else:
                r = (p1-p2).length() / (2 * math.sin(phi) + (phi==0))
                radius.append(r)

        return radius
    
    @cached_property('ballooning_phi', 'prof1', 'prof2')
    def ballooning_tension_factors(self) -> list[float]:
        prof1 = self.prof1.curve.nodes
        prof2 = self.prof2.curve.nodes
        tension: list[float] = []
        for p1, p2, phi in zip(prof1, prof2, self.ballooning_phi):
            value =  2. * math.tan(phi)
            if value > 1e-10:
                value = 1/value
            
            tension.append(value * (p1-p2).length())
        
        return tension

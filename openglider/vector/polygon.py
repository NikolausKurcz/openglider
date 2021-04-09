import numpy
import euklid
import math

from openglider.vector.polyline import PolyLine2D
from openglider.vector.functions import cut, rotation_2d, vector_angle, norm


class Polygon2D(PolyLine2D):
    @property
    def isclosed(self):
        return self.data[0] == self.data[-1]

    def close(self):
        """
        Close the endings of the polygon using a cut.
        Return: success
        """
        try:
            thacut = cut(self.data[0], self.data[1], self.data[-2], self.data[-1])
            if thacut[1] <= 1 and 0 <= thacut[2]:
                self.data[0] = thacut[0]
                self.data[-1] = thacut[0]
                return True
        except ArithmeticError:
            return False

    #@cached-property(self)
    @property
    def centerpoint(self):
        # todo: http://en.wikipedia.org/wiki/Polygon#Area_and_centroid
        """
        Return the average point of the polygon.
        """
        return sum(self.data) / len(self.data)

    @property
    def area(self):
        # http://en.wikipedia.org/wiki/Polygon#Area_and_centroid
        area = 0
        n = len(self)-1
        for i in range(len(self)):
            i2 = (i+1) % n
            area += self[i][0]*self[i2][1] - self[i][1]*self[i2][0]

        return area/2

    def contains_point(self, point):
        """
        Check if a Polygon contains a point or not.
        reference: http://en.wikipedia.org/wiki/Point_in_polygon

        :returns: boolean
        """
        # using ray-casting-algorithm
        cuts = self.cut(point, self.centerpoint, cut_only_positive=True)
        return bool(sum(1 for _ in cuts) % 2)
        # todo: alternative: winding number


class CirclePart(object):
    """
    "A piece of the cake"
    
       /) <-- p1
      /   )
     /     )
    |       ) <-- p2
     \     )
      \   )
       \) <-- p3
    """
    def __init__(self, p1, p2, p3):
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3

        l1 = numpy.array(p2) - numpy.array(p1)
        l2 = numpy.array(p3) - numpy.array(p2)

        n1 = numpy.array([-l1[1], l1[0]])
        n2 = numpy.array([-l2[1], l2[0]])

        c1 = p1 + l1/2
        c2 = p2 + l2/2

        d1 = c1 + n1
        d2 = c2 + n2

        self.center, i, k = cut(c1, d1, c2, d2)
        self.r = numpy.array(p1) - self.center

    def get_sequence(self, num=20):
        lst = []
        end = vector_angle(self.r, numpy.array(self.p3) - self.center)
        for angle in numpy.linspace(0, end, num):
            lst.append(self.center + rotation_2d(angle).dot(self.r))

        return PolyLine2D(lst)

    def _repr_svg_(self):

        svg = "<svg>"
        def point(p, color="red"):
            return '<circle cx="{}" cy="{}" r="1" stroke="{}" fill="transparent" stroke-width="5"/>'.format(p[0], p[1], color)

        svg += point(self.center, "blue")


        svg += point(self.p1)
        svg += point(self.p2)
        svg += point(self.p3)

        svg += "</svg>"
        return svg


class Ellipse(object):
    def __init__(self, center, radius, height, rotation=0):
        self.center = center
        self.radius = radius
        self.height = height
        self.rotation = rotation

    def get_sequence(self, num=20):
        points = []

        for i in range(num):
            angle = math.pi * 2 * (i/(num-1))
            diff = euklid.vector.Vector2D([math.cos(angle), self.height*math.sin(angle)]) * self.radius
            
            points.append(self.center + diff)

        line = euklid.vector.PolyLine2D(points)

        return line.rotate(self.rotation, self.center)

    @classmethod
    def from_center_p2(cls, center, p2, aspect_ratio=1):
        diff = p2 - center
        radius = diff.length()
        diff_0 = diff.normalized()

        rotation = math.atan2(diff_0[1], diff_0[0])

        return cls(center, radius, aspect_ratio, rotation)


class Circle(Ellipse):
    def __init__(self, center, radius, rotation=0):
        super().__init__(center, radius, radius, rotation)
    
    @classmethod
    def from_p1_p2(cls, p1, p2):
        center = (p1 + p2)*0.5
        radius = norm(p2 - p1)*0.5
        return cls(center, radius)
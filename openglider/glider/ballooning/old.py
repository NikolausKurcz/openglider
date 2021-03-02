import copy

import euklid

from openglider.glider.ballooning.base import BallooningBase


class Ballooning(BallooningBase):

    def __init__(self, f_upper: euklid.vector.Interpolation, f_lower: euklid.vector.Interpolation):
        self.upper: euklid.vector.Interpolation = f_upper
        self.lower: euklid.vector.Interpolation = f_lower

    def __json__(self):
        return {'f_upper': self.upper,
                'f_lower': self.lower}

    def __getitem__(self, xval):
        """Get Ballooning Value (%) for a certain XValue"""
        if -1 <= xval < 0:
            #return self.upper.xpoint(-xval)[1]
            return self.upper.get_value(-xval)
        elif 0 <= xval <= 1:
            #return -self.lower.xpoint(xval)[1]
            return self.lower.get_value(xval)
        else:
            raise ValueError("Value {} not between -1 and 1".format(xval))

    def __add__(self, other):
        """Add another Ballooning to this one, needed for merging purposes"""
        upper = []
        for point in self.upper.nodes:
            upper.append([point[0], point[1]+other.upper.get_value(point[0])])
        lower = []
        for point in self.lower.nodes:
            lower.append([point[0], point[1]+other.lower.get_value(point[0])])

        return Ballooning(euklid.vector.Interpolation(upper), euklid.vector.Interpolation(lower))

    def __imul__(self, val):
        for point in self.upper.nodes:
            point[1] *= val
        for point in self.lower.nodes:
            point[1] *= val
        return self

    def __mul__(self, value):
        """Multiply Ballooning With a Value"""
        new = self.copy()
        new *= value
        return new

    def copy(self):
        return copy.deepcopy(self)

    def mapx(self, xvals):
        return [self[i] for i in xvals]

    @property
    def amount_maximal(self):
        return max(max([p[1] for p in self.upper]), max([p[1] for p in self.lower]))

    @property
    def amount_integral(self):
        # Integration of 2-points always:
        amount = 0
        for curve in [self.upper, self.lower]:
            for p1, p2 in zip(curve[:-1], curve[1:]):
                # points: (x1,y1), (x2,y2)
                #     _ p2
                # p1_/ |
                #  |   |
                #  |___|
                amount += (p1[1] + (p2[1]-p1[1])/2) * (p2[0]-p1[0])
        return amount / 2

    @amount_maximal.setter
    def amount_maximal(self, amount):
        factor = float(amount) / self.amount_maximal
        self.scale(factor)

    def scale(self, factor):
        self.upper.scale(1, factor)
        self.lower.scale(1, factor)

    def close_trailing_edge(self, start_x):
        # ballooning -> 0 on trailing edge
        for curve in (self.upper, self.lower):
            data = []
            for x, y in curve.data:
                if x > start_x:
                    # t_e_c -> 1
                    # 1 -> 0
                    # steigung = 1/(1-t_e_c)
                    # d = 1
                    t_e_c = start_x
                    y = y * (1 - (x-t_e_c)/(1-t_e_c))
                    #y = (1-x) * y

                data.append((x, y))

            curve.data = data

    def _repr_svg_(self):
        import svgwrite
        import svgwrite.container

        height = self.amount_maximal * 2

        drawing = svgwrite.Drawing(size=[800, 800*height])

        drawing.viewbox(0, -height/2, 1, height)

        g = svgwrite.container.Group()
        g.scale(1, -1)
        upper = drawing.polyline(self.upper.data, style="stroke:black; vector-effect: non-scaling-stroke; fill: none;")
        lower = drawing.polyline([(p[0], -p[1]) for p in self.lower.data], style="stroke:black; vector-effect: non-scaling-stroke; fill: none;")
        g.add(upper)
        g.add(lower)
        drawing.add(g)

        return drawing.tostring()


class BallooningBezier(Ballooning):
    num_points = 100
    def __init__(self, upper=None, lower=None, name="ballooning"):
        super(BallooningBezier, self).__init__(None, None)
        upper = upper or [[0, 0], [0.1, 0], [0.2, 0.14], [0.8, 0.14], [0.9, 0], [1, 0]]
        lower = lower or [[0, 0], [0.1, 0], [0.2, 0.14], [0.8, 0.14], [0.9, 0], [1, 0]]

        self.upper_spline = euklid.vector.BSplineCurve(upper)
        self.lower_spline = euklid.vector.BSplineCurve(lower)

        self.upper_spline.controlpoints.nodes[0][0] = 0
        self.upper_spline.controlpoints.nodes[-1][0] = 1
        self.lower_spline.controlpoints.nodes[0][0] = 0
        self.lower_spline.controlpoints.nodes[-1][0] = 1
        
        self.name = name
        self.apply_splines()

    def __json__(self):
        return {"upper": [list(p) for p in self.upper_spline.controlpoints],
                "lower": [list(p) for p in self.lower_spline.controlpoints]}

    @property
    def points(self):
        upper = list(self.upper_spline.get_sequence(self.num_points))
        lower = [(p[0], -p[1]) for p in self.lower_spline.get_sequence()][::-1]
        return upper + lower

    def get_points(self, n=150):
        n_2 = int(n / 2)
        upper = [(-p[0], p[1]) for p in self.upper_spline.get_sequence(n_2)][::-1]
        lower = [p for p in self.lower_spline.get_sequence(n_2)]
        return upper + lower

    def apply_splines(self):
        self.upper = euklid.vector.Interpolation(self.upper_spline.get_sequence(self.num_points).nodes)
        self.lower = euklid.vector.Interpolation(self.lower_spline.get_sequence(self.num_points).nodes)

    def __imul__(self, factor):  # TODO: Check consistency
        """Multiplication of BezierBallooning"""
        # Multiplicate as normal interpolated ballooning, then refit
        #Ballooning.__imul__(self, factor)
        #self.upper_spline.fit(self.upper.data)
        #self.lower_spline.fit(self.lower.data)
        self.controlpoints = [
            [[x[0], x[1]*factor] for x in lst] for lst in self.controlpoints
        ]
        return self

    @property
    def numpoints(self):
        return len(self.upper)

    @numpoints.setter
    def numpoints(self, numpoints):
        Ballooning.__init__(self, self.upper_spline.interpolation(numpoints), self.lower_spline.interpolation(numpoints))

    @property
    def controlpoints(self):
        return self.upper_spline.controlpoints, self.lower_spline.controlpoints

    @controlpoints.setter
    def controlpoints(self, controlpoints):
        upper, lower = controlpoints
        if upper is not None:
            self.upper_spline.controlpoints = upper
        if lower is not None:
            self.lower_spline.controlpoints = lower
        Ballooning.__init__(self, self.upper_spline.interpolation(), self.lower_spline.interpolation())

    def scale(self, factor):
        super(BallooningBezier, self).scale(factor)
        self.upper_spline.scale(1, factor)
        self.lower_spline.scale(1, factor)

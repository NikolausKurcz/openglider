from openglider.vector.spline.bezier import Bezier, SymmetricBezier
from openglider.utils import dualmethod

class BSplineBase():
    def __init__(self, degree=3):
        self.degree = degree
        self.bases = {}

    def __call__(self, numpoints):      # number of controlpoints
        if numpoints not in self.bases and True:
            knots = self.make_knot_vector(self.degree, numpoints)
            basis = [self.get_basis(self.degree, i, knots) for i in range(numpoints)]
            self.bases[numpoints] = basis

        return self.bases[numpoints]

    def get_basis(self, degree, i, knots):
        """ Returns a basis_function for the given degree """
        if degree == 0:
            def basis_function(t):
                """The basis function for degree = 0 as per eq. 7"""
                t_this = knots[i]
                t_next = knots[i+1]
                return t_next >= t > t_this
        else:

            def basis_function(t):
                """The basis function for degree > 0 as per eq. 8"""
                if i == t == 0:
                    return 1
                out = 0.
                t_this = knots[i]
                t_next = knots[i+1]
                t_precog  = knots[i+degree]
                t_horizon = knots[i+degree+1]

                top = (t-t_this)
                bottom = (t_precog-t_this)

                if bottom != 0:
                    out = top/bottom * self.get_basis(degree-1, i, knots)(t)

                top = (t_horizon-t)
                bottom = (t_horizon-t_next)
                if bottom != 0:
                    out += top/bottom * self.get_basis(degree-1, i+1, knots)(t)
                return out

        return basis_function



    def make_knot_vector(self, degree, num_points):
        """
        Create knot vectors
        """

        total_knots = num_points+degree+1
        outer_knots = degree
        inner_knots = total_knots - 2*outer_knots

        knots = [0.]*outer_knots
        knots += [i/(inner_knots-1.) for i in range(inner_knots)]
        knots += [1.]*outer_knots
        return knots


class BSpline(Bezier):
    basefactory = BSplineBase(2)

    def __json__(self):
        out = super(BSpline, self).__json__()
        out["degree"] = self.basefactory.degree
        return out

    @classmethod
    def __from_json__(cls, controlpoints, degree):
        obj = super(BSpline, cls).__from_json__(controlpoints)
        obj.basefactory = BSplineBase(degree)
        return obj

class BSpline3(BSpline):
    basefactory = BSplineBase(3)


class SymmetricBSpline(SymmetricBezier):
    basefactory = BSplineBase(2)

    def __json__(self):
        out = super(SymmetricBSpline, self).__json__()
        out["degree"] = self.basefactory.degree
        return out

    @classmethod
    def __from_json__(cls, controlpoints, degree):
        obj = super(SymmetricBSpline, cls).__from_json__(controlpoints)
        obj.basefactory = BSplineBase(degree)
        return obj

class SymmetricBSpline3(SymmetricBSpline):
    basefactory = BSplineBase(3)

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import numpy as np

    data = [[-0.2, 0.], [-0.5, 0.5], [-1., 0.], [-2, 3]]
    curve = SymmetricBSpline(data)
    values = curve.get_sequence(20)
    cp = curve.controlpoints
    curve_pts = [curve(i) for i in np.linspace(0.,  1, 100)]
    # for i in curve.basefactory(5):
    #     plt.plot(*zip(*[[x, i(x)] for x in np.linspace(0., 1, 100)]))
    plt.show()
    plt.plot(*zip(*values))
    # plt.plot(*zip(*curve_pts))
    plt.plot(*zip(*curve.data))
    plt.plot(*zip(*data))
    plt.show()
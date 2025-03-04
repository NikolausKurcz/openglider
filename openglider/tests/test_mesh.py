import unittest


from openglider.tests.common import GliderTestCase

from openglider.mesh import Mesh, Vertex, Polygon
from openglider.utils.distribution import Distribution


class TestMesh(GliderTestCase):
    def test_mesh(self) -> None:
        p1 = Vertex(0, 0, 0)
        p2 = Vertex(1, 0, 0)
        p3 = Vertex(0, 1, 0)
        p4 = Vertex(1, 1, 0)
        p5 = Vertex(0, 0, 0)
        a = Polygon([p1, p2, p3, p4])
        b = Polygon([p1, p2, p4, p5])
        m1 = Mesh({"a": [a]}, boundary_nodes={"j": list(a)})
        m2 = Mesh({"b": [b]}, boundary_nodes={"j": list(b)})
        m3 = m1 + m2
        m3.delete_duplicates()
        for vertex in a:
            matches = [vertex.is_equal(p) for p in m3.vertices]
            self.assertTrue(any(matches))

    def test_glider_mesh(self) -> None:
        dist = Distribution.from_nose_cos_distribution(30, 0.2)

        self.glider.profile_x_values = list(dist)
        m = Mesh(name="glider_mesh")
        for cell in self.glider.cells[1:-1]:
            m += cell.get_mesh(0)
        for rib in self.glider.ribs:
            m += rib.get_mesh()
        m.delete_duplicates()
        m.get_indexed()



if __name__ == '__main__':
    unittest.main(verbosity=2)

import sys
import os
import unittest

try:
    import openglider
except ImportError:
    def stepup(path, num):
        if num == 0:
            return path
        else:
            return stepup(os.path.dirname(path), num-1)
    sys.path.append(stepup(__file__,3))
    print(sys.path)
    import openglider

import openglider.glider
from openglider.glider.parametric import ParametricGlider

import_dir = os.path.dirname(os.path.abspath(__file__))
test_dir = os.path.dirname(import_dir)
#demokite = import_dir + '/demokite.ods'
# demokite = import_dir + "/glider2d_midrip.json"
demokite = import_dir + "/demokite.json"


class TestCase(unittest.TestCase):
    @classmethod
    def import_glider(cls):
        glider_2d = cls.import_glider_2d()
        return glider_2d.get_glider_3d()

    @classmethod
    def import_glider_2d(cls):
        return openglider.load(demokite)
        #return ParametricGlider.import_ods(path=demokite)

    def assertEqualGlider(self, glider1, glider2, precision=None):
        self.assertEqual(len(glider1.ribs), len(glider2.ribs))
        self.assertEqual(len(glider1.cells), len(glider2.cells))
        for rib_no, (rib_1, rib_2) in enumerate(zip(glider1.ribs, glider2.ribs)):
            # test profile_3d this should include align, profile,...
            for xyz_1, xyz_2 in zip(rib_1.profile_3d.curve.nodes, rib_2.profile_3d.curve.nodes):
                for i, (_p1, _p2) in enumerate(zip(xyz_1, xyz_2)):
                    self.assertAlmostEqual(_p1, _p2, places=precision, msg="Not matching at Rib {}, Coordinate {}; {}//{}".format(rib_no, i, _p1, _p2))
                    # todo: expand test: lines, diagonals,...

    def assertEqualGlider2D(self, glider1, glider2):
        self.assertEqual(glider1.shape.cell_num, glider2.shape.cell_num)

if __name__ == "__main__":
    glider = ParametricGlider.import_ods("./demokite.ods")
    with open(demokite, "w") as outfile:
        openglider.jsonify.dump(glider, outfile)
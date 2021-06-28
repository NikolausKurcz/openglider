#! /usr/bin/python2
# -*- coding: utf-8; -*-
#
# (c) 2013 booya (http://booya.at)
#
# This file is part of the OpenGlider project.
#
# OpenGlider is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# OpenGlider is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenGlider.  If not, see <http://www.gnu.org/licenses/>.

import numpy as np

def depth(arg):
    try:
        return max([depth(i) for i in arg]) + 1
    except TypeError:  # Not a list anymore
        return 1


def arrtype(arg):
    """
    return type of a vector list: 2d-point (1), list of 2d-points (2), 3d-point (3), list of 3d-points (4)
    """
    ##2d-point//argof2d-points//3d-point//argof3d-points
    ##2d-p: depth 1
    ##equivalent np.rank?

    # TODO: Room for improvement here!
    # todo: remove!

    if depth(arg) == 2:
        if len(arg) == 2:
            return 1
        elif len(arg) == 3:
            return 3
        else:
            return 0
    elif depth(arg) == 3:
        if [depth(i) for i in arg] == [2 for i in arg]:
            if [len(i) for i in arg] == [2 for i in arg]:
                return 2
            elif [len(i) for i in arg] == [3 for i in arg]:
                return 4
            else:
                return 0
        else:
            return 0
    else:
        return 0

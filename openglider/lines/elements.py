import logging

import numpy as np

from openglider.lines.line import Line


logger = logging.getLogger(__name__)

class SagMatrix():
    def __init__(self, number_of_lines: int):
        # matrix with (i) => angle / (i+1) => offset_lower_node
        size = number_of_lines * 2
        self.matrix = np.zeros([size, size])
        self.rhs = np.zeros(size)
        self.solution = np.zeros(size)
        self.line_indices: dict[Line, int] = {}

    def __str__(self) -> str:
        return str(self.matrix) + "\n" + str(self.rhs)
    
    def line_index(self, line: Line) -> int:
        if line not in self.line_indices:
            self.line_indices[line] = len(self.line_indices)
        
        return self.line_indices[line]

    def insert_type_0_lower(self, line: Line) -> None:
        """
        fixed lower node
        """
        i = self.line_index(line)
        self.matrix[2 * i + 1, 2 * i + 1] = 1.  # set offset_lower = 0

    def insert_type_1_lower(self, line: Line, lower_line: Line) -> None:
        """
        free lower node
        """
        i = self.line_index(line)
        j = self.line_index(lower_line)
        self.matrix[2 * i + 1, 2 * i + 1] = 1.
        self.matrix[2 * i + 1, 2 * j + 1] = -1.
        self.matrix[2 * i + 1, 2 * j] = -lower_line.length_projected
        self.rhs[2 * i + 1] = -lower_line.ortho_pressure * \
            lower_line.length_projected ** 2 / lower_line.force_projected / 2
        
        # offset_lower = offset_lower(lower) + angle_lower * length_proj

    def insert_type_1_upper(self, line: Line, upper_lines: list[Line]) -> None:
        """
        free upper node
        """
        i = self.line_index(line)
        self.matrix[2 * i, 2 * i] = 1

        for upper_line in upper_lines:
            j = self.line_index(upper_line)
            self.matrix[2*i, 2*j] = -1 / len(upper_lines)

        self.rhs[2 * i] = line.ortho_pressure * \
            line.length_projected / line.force_projected

    def insert_type_2_upper(self, line: Line) -> None:
        """
        Fixed upper node
        """
        i = self.line_index(line)
        self.matrix[2 * i, 2 * i] = line.length_projected
        self.matrix[2 * i, 2 * i + 1] = 1.
        self.rhs[2 * i] = line.ortho_pressure * \
            line.length_projected ** 2 / line.force_projected / 2

    def solve_system(self) -> None:
        self.solution = np.linalg.solve(self.matrix, self.rhs)

    def get_sag_parameters(self, line: Line) -> tuple[float, float]:
        line_nr = self.line_index(line)
        return (
            self.solution[line_nr * 2],
            self.solution[line_nr * 2 + 1]
            )


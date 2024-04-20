import csv
import logging
from pathlib import Path

from openglider.materials.material import Material
from openglider.config import config

logger = logging.getLogger(__name__)
dirname = Path(__file__).parent.absolute()

class MaterialRegistry:
    base_type = Material
    def __init__(self, *paths: Path):
        self.materials: dict[str, Material] = {}
        for path in paths:
            if path.exists():
                self.read_csv(path)
            else:
                logger.warning(f"file {path} not found")

    def read_csv(self, path: Path):
        with open(path) as infile:
            data = csv.reader(infile)
            next(data)  # skip header line

            for line in data:
                material = Material(
                    manufacturer=line[0],
                    name=line[1],
                    weight=line[2],
                    color=line[3],
                    color_code=line[4]
                )
                self.materials[str(material)] = material


    def __repr__(self) -> str:
        out = "Materials: "
        for material_name in self.materials:
            out += f"\n    - {material_name}"

        return out
    
    def get(self, name: str) -> Material:
        name = name.lower()
        if name in self.materials:
            return self.materials[name]

        #logger.warning(f"material not found: {name}")

        return self.base_type(name=name)


cloth = MaterialRegistry(
    dirname / "cloth.csv",
    config.home_directory / "materials.csv"
)
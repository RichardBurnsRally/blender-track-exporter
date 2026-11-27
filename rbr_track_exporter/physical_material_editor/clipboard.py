from dataclasses import dataclass
from typing import Optional

from ..types import MaterialMap
from .properties import RBRMaterialMap


@dataclass
class PhysicalMaterialClipboard:
    """The material clipboard allows users to copy and paste material bitmaps
    between different regions, textures, and track settings.
    """

    clipboard_material: Optional[MaterialMap] = None

    def copy(self, material_map: RBRMaterialMap) -> None:
        self.clipboard_material = material_map.to_format()

    def paste(self, material_map: RBRMaterialMap) -> bool:
        """Paste from the clipboard. If the clipboard is empty, returns False."""
        if self.clipboard_material is None:
            return False
        material_map.set_from_format(self.clipboard_material)
        return True


# In memory clipboard for physical material maps.
GLOBAL_PHYSICAL_MATERIAL_CLIPBOARD = PhysicalMaterialClipboard()

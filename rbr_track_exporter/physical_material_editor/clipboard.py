from dataclasses import dataclass
from typing import Optional

import bpy

from ..types import MaterialMap
from .properties import RBRMaterialMaps


@dataclass
class PhysicalMaterialClipboard:
    """The material clipboard allows users to copy and paste material bitmaps
    between different regions, textures, and track settings.
    """

    clipboard_material: Optional[MaterialMap] = None

    def copy(
        self,
        material_maps: "bpy.types.bpy_prop_collection[RBRMaterialMaps]",
        material_index: int,
    ) -> None:
        """Copy to the clipboard"""
        matmap = material_maps[material_index].get_active_map()
        self.clipboard_material = matmap.to_format()

    def paste(
        self,
        material_maps: "bpy.types.bpy_prop_collection[RBRMaterialMaps]",
        material_index: int,
    ) -> bool:
        """Paste from the clipboard. If the clipboard is empty, returns False.
        Successful pastes return True."""
        if self.clipboard_material is None:
            return False
        matmap = material_maps[material_index].get_active_map()
        matmap.set_from_format(self.clipboard_material)
        return True


# In memory clipboard for physical material maps.
GLOBAL_PHYSICAL_MATERIAL_CLIPBOARD = PhysicalMaterialClipboard()

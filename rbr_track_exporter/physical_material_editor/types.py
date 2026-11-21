from __future__ import annotations

import enum
from typing import Optional, assert_never

from mathutils import Vector


# This used to live in properties, but I had to move it here because of
# https://developer.blender.org/T63713
class GrabHandle(enum.Enum):
    TOP_LEFT = 1
    TOP_MID = 2
    TOP_RIGHT = 3
    MID_LEFT = 4
    MID_RIGHT = 5
    BOTTOM_LEFT = 6
    BOTTOM_MID = 7
    BOTTOM_RIGHT = 8

    def position_relative(self) -> Vector:
        if self is GrabHandle.TOP_LEFT:
            return Vector((0, 1))
        elif self is GrabHandle.TOP_MID:
            return Vector((0.5, 1))
        elif self is GrabHandle.TOP_RIGHT:
            return Vector((1, 1))
        elif self is GrabHandle.MID_LEFT:
            return Vector((0, 0.5))
        elif self is GrabHandle.MID_RIGHT:
            return Vector((1, 0.5))
        elif self is GrabHandle.BOTTOM_LEFT:
            return Vector((0, 0))
        elif self is GrabHandle.BOTTOM_MID:
            return Vector((0.5, 0))
        elif self is GrabHandle.BOTTOM_RIGHT:
            return Vector((1, 0))
        assert_never(self)

    def is_grabbable(self, repeat_x: bool, repeat_y: bool) -> bool:
        """Only handles which do not lie on a repeated edge are grabbable."""
        if self is GrabHandle.TOP_LEFT:
            return not repeat_x and not repeat_y
        elif self is GrabHandle.TOP_MID:
            return not repeat_y
        elif self is GrabHandle.TOP_RIGHT:
            return not repeat_x and not repeat_y
        elif self is GrabHandle.MID_LEFT:
            return not repeat_x
        elif self is GrabHandle.MID_RIGHT:
            return not repeat_x
        elif self is GrabHandle.BOTTOM_LEFT:
            return not repeat_x and not repeat_y
        elif self is GrabHandle.BOTTOM_MID:
            return not repeat_y
        elif self is GrabHandle.BOTTOM_RIGHT:
            return not repeat_x and not repeat_y
        assert_never(self)

    def flip_x(self) -> GrabHandle:
        """Flip a grab handle in the X axis (left becomes right)"""
        if self is GrabHandle.TOP_LEFT:
            return GrabHandle.TOP_RIGHT
        elif self is GrabHandle.TOP_MID:
            return GrabHandle.TOP_MID
        elif self is GrabHandle.TOP_RIGHT:
            return GrabHandle.TOP_LEFT
        elif self is GrabHandle.MID_LEFT:
            return GrabHandle.MID_RIGHT
        elif self is GrabHandle.MID_RIGHT:
            return GrabHandle.MID_LEFT
        elif self is GrabHandle.BOTTOM_LEFT:
            return GrabHandle.BOTTOM_RIGHT
        elif self is GrabHandle.BOTTOM_MID:
            return GrabHandle.BOTTOM_MID
        elif self is GrabHandle.BOTTOM_RIGHT:
            return GrabHandle.BOTTOM_LEFT
        assert_never(self)

    def flip_y(self) -> GrabHandle:
        """Flip a grab handle in the Y axis (top becomes bottom)"""
        if self is GrabHandle.TOP_LEFT:
            return GrabHandle.BOTTOM_LEFT
        elif self is GrabHandle.TOP_MID:
            return GrabHandle.BOTTOM_MID
        elif self is GrabHandle.TOP_RIGHT:
            return GrabHandle.BOTTOM_RIGHT
        elif self is GrabHandle.MID_LEFT:
            return GrabHandle.MID_LEFT
        elif self is GrabHandle.MID_RIGHT:
            return GrabHandle.MID_RIGHT
        elif self is GrabHandle.BOTTOM_LEFT:
            return GrabHandle.TOP_LEFT
        elif self is GrabHandle.BOTTOM_MID:
            return GrabHandle.TOP_MID
        elif self is GrabHandle.BOTTOM_RIGHT:
            return GrabHandle.TOP_RIGHT
        assert_never(self)

    def flip(self, x: bool, y: bool) -> Optional[GrabHandle]:
        """Flip a grab handle along x and y axes, returns None if the grab
        handle is not changed by the flip."""
        handle = self
        if x:
            handle = handle.flip_x()
        if y:
            handle = handle.flip_y()
        if handle is self:
            return None
        else:
            return handle

from __future__ import annotations
from dataclasses import dataclass
import enum
from typing import Callable, List, Literal, Optional, Set, TypeVar, assert_never

from mathutils import Vector

OperatorReturn = Set[
    Literal["RUNNING_MODAL", "CANCELLED", "FINISHED", "PASS_THROUGH", "INTERFACE"]
]


class PacenoteId(enum.Enum):
    NOTE_HAIRPINLEFT = 0
    NOTE_LEFT90 = 1
    NOTE_KLEFT = 2
    NOTE_MEDIUMLEFT = 3
    NOTE_FASTLEFT = 4
    NOTE_EASYLEFT = 5
    NOTE_EASYRIGHT = 6
    NOTE_FASTRIGHT = 7
    NOTE_MEDIUMRIGHT = 8
    NOTE_KRIGHT = 9
    NOTE_RIGHT90 = 10
    NOTE_HAIRPINRIGHT = 11
    NOTE_TWISTY = 12
    NOTE_DISTANCE = 13
    NOTE_NARROWS = 14  # Also used as flag
    NOTE_WIDEOUT = 15  # Also used as flag
    NOTE_OVERCREST = 16
    NOTE_FORD = 17
    NOTE_CARE = 18
    NOTE_BUMP = 19
    NOTE_JUMP = 20

    # These actually control the timing
    EVENT_START = 21
    EVENT_FINISH = 22
    EVENT_CHECKPOINT = 23
    EVENT_ENDSTAGE = 24

    NOTE_FLATRIGHT = 25
    NOTE_FLATLEFT = 26
    NOTE_BRIDGE = 27
    NOTE_GOSTRAIGHT = 28
    NOTE_KEEPRIGHT = 29
    NOTE_KEEPLEFT = 30
    NOTE_KEEPMIDDLE = 31
    NOTE_CAUTION = 32

    def is_checkpoint(self) -> bool:
        return self is PacenoteId.EVENT_CHECKPOINT

    def is_event(self) -> bool:
        return any(
            [
                self is PacenoteId.EVENT_START,
                self is PacenoteId.EVENT_FINISH,
                self is PacenoteId.EVENT_CHECKPOINT,
                self is PacenoteId.EVENT_ENDSTAGE,
            ]
        )

    @staticmethod
    def nicely_ordered_universe() -> List[PacenoteId]:
        """Return all PacenoteIds in a nice order"""
        return [
            PacenoteId.EVENT_START,
            PacenoteId.EVENT_FINISH,
            PacenoteId.EVENT_CHECKPOINT,
            PacenoteId.EVENT_ENDSTAGE,
            PacenoteId.NOTE_HAIRPINLEFT,
            PacenoteId.NOTE_LEFT90,
            PacenoteId.NOTE_KLEFT,
            PacenoteId.NOTE_MEDIUMLEFT,
            PacenoteId.NOTE_FASTLEFT,
            PacenoteId.NOTE_EASYLEFT,
            PacenoteId.NOTE_FLATLEFT,
            PacenoteId.NOTE_HAIRPINRIGHT,
            PacenoteId.NOTE_RIGHT90,
            PacenoteId.NOTE_KRIGHT,
            PacenoteId.NOTE_MEDIUMRIGHT,
            PacenoteId.NOTE_FASTRIGHT,
            PacenoteId.NOTE_EASYRIGHT,
            PacenoteId.NOTE_FLATRIGHT,
            PacenoteId.NOTE_DISTANCE,
            PacenoteId.NOTE_CARE,
            PacenoteId.NOTE_CAUTION,
            PacenoteId.NOTE_TWISTY,
            PacenoteId.NOTE_NARROWS,
            PacenoteId.NOTE_WIDEOUT,
            PacenoteId.NOTE_FORD,
            PacenoteId.NOTE_OVERCREST,
            PacenoteId.NOTE_BUMP,
            PacenoteId.NOTE_JUMP,
            PacenoteId.NOTE_BRIDGE,
            PacenoteId.NOTE_GOSTRAIGHT,
            PacenoteId.NOTE_KEEPRIGHT,
            PacenoteId.NOTE_KEEPLEFT,
            PacenoteId.NOTE_KEEPMIDDLE,
        ]

    def pretty(self) -> str:
        if self is PacenoteId.NOTE_HAIRPINLEFT:
            return "Left Hairpin"
        elif self is PacenoteId.NOTE_LEFT90:
            return "Left 90"
        elif self is PacenoteId.NOTE_KLEFT:
            return "Left K"
        elif self is PacenoteId.NOTE_MEDIUMLEFT:
            return "Left Medium"
        elif self is PacenoteId.NOTE_FASTLEFT:
            return "Left Fast"
        elif self is PacenoteId.NOTE_EASYLEFT:
            return "Left Easy"
        elif self is PacenoteId.NOTE_FLATLEFT:
            return "Left Flat"

        if self is PacenoteId.NOTE_HAIRPINRIGHT:
            return "Right Hairpin"
        elif self is PacenoteId.NOTE_RIGHT90:
            return "Right 90"
        elif self is PacenoteId.NOTE_KRIGHT:
            return "Right K"
        elif self is PacenoteId.NOTE_MEDIUMRIGHT:
            return "Right Medium"
        elif self is PacenoteId.NOTE_FASTRIGHT:
            return "Right Fast"
        elif self is PacenoteId.NOTE_EASYRIGHT:
            return "Right Easy"
        elif self is PacenoteId.NOTE_FLATRIGHT:
            return "Right Flat"

        elif self is PacenoteId.NOTE_TWISTY:
            return "Twisty"
        elif self is PacenoteId.NOTE_DISTANCE:
            return "Distance"
        elif self is PacenoteId.NOTE_NARROWS:
            return "Narrows"
        elif self is PacenoteId.NOTE_WIDEOUT:
            return "Wide Out"
        elif self is PacenoteId.NOTE_OVERCREST:
            return "Over Crest"
        elif self is PacenoteId.NOTE_FORD:
            return "Ford"
        elif self is PacenoteId.NOTE_CARE:
            return "Care"
        elif self is PacenoteId.NOTE_BUMP:
            return "Bump"
        elif self is PacenoteId.NOTE_JUMP:
            return "Jump"
        elif self is PacenoteId.NOTE_BRIDGE:
            return "Bridge"
        elif self is PacenoteId.NOTE_GOSTRAIGHT:
            return "Go Straight"
        elif self is PacenoteId.NOTE_KEEPRIGHT:
            return "Keep Right"
        elif self is PacenoteId.NOTE_KEEPLEFT:
            return "Keep Left"
        elif self is PacenoteId.NOTE_KEEPMIDDLE:
            return "Keep Middle"
        elif self is PacenoteId.NOTE_CAUTION:
            return "Caution"

        elif self is PacenoteId.EVENT_START:
            return "Event: Start"
        elif self is PacenoteId.EVENT_FINISH:
            return "Event: Finish"
        elif self is PacenoteId.EVENT_CHECKPOINT:
            return "Event: Split"
        elif self is PacenoteId.EVENT_ENDSTAGE:
            return "Event: End of Stage"
        assert_never(self)


class MaterialId(enum.Enum):
    UNDEFINED = 0
    GRAVEL_FINE_DEEPER_DRY = 1
    GRAVEL_FINE_DEEPER_DAMP = 2
    GRAVEL_FINE_DEEPER_WET = 3
    GRAVEL_MEDIUM_DEEPER_DRY = 5
    GRAVEL_MEDIUM_DEEPER_DAMP = 6
    GRAVEL_MEDIUM_DEEPER_WET = 7
    GRAVEL_FINE_DEEP_DRY = 9
    GRAVEL_FINE_DEEP_DAMP = 10
    GRAVEL_FINE_DEEP_WET = 11
    GRAVEL_MEDIUM_DEEP_DRY = 13
    GRAVEL_MEDIUM_DEEP_DAMP = 14
    GRAVEL_MEDIUM_DEEP_WET = 15
    GRAVEL_FINE_SHALLOW_DRY = 17
    GRAVEL_FINE_SHALLOW_DAMP = 18
    GRAVEL_FINE_SHALLOW_WET = 19
    GRAVEL_MEDIUM_SHALLOW_DRY = 21
    GRAVEL_MEDIUM_SHALLOW_DAMP = 22
    GRAVEL_MEDIUM_SHALLOW_WET = 23
    SPRET_BUSH_SMALL = 24
    SPRET_BUSH_MEDIUM = 25
    SPRET_BUSH_LARGE = 26
    LOV_BUSH_SMALL = 27
    LOV_BUSH_MEDIUM = 28
    LOV_BUSH_LARGE = 29
    TREE_SMALL = 30
    TREE_MEDIUM = 31
    TREE_LARGE = 32
    GRAVEL_COARSE_DEEPER_DRY = 33
    GRAVEL_COARSE_DEEPER_DAMP = 34
    GRAVEL_COARSE_DEEPER_WET = 35
    TARMAC_FINE_CLEAN_DRY = 37
    TARMAC_FINE_CLEAN_DAMP = 38
    TARMAC_FINE_CLEAN_WET = 39
    GRAVEL_COARSE_DEEP_DRY = 41
    GRAVEL_COARSE_DEEP_DAMP = 42
    GRAVEL_COARSE_DEEP_WET = 43
    TARMAC_FINE_SPRINKLED_DRY = 45
    TARMAC_FINE_SPRINKLED_DAMP = 46
    TARMAC_FINE_SPRINKLED_WET = 47
    GRAVEL_COARSE_SHALLOW_DRY = 49
    GRAVEL_COARSE_SHALLOW_DAMP = 50
    GRAVEL_COARSE_SHALLOW_WET = 51
    TARMAC_FINE_COVERED_DRY = 53
    TARMAC_FINE_COVERED_DAMP = 54
    TARMAC_FINE_COVERED_WET = 55
    ROCK_SMALL = 56
    ROCK_MEDIUM = 57
    ROCK_LARGE = 58
    TRUNK_SMALL = 59
    TRUNK_MEDIUM = 60
    TRUNK_LARGE = 61
    SNOWWALL = 62
    METAL_POLE = 63
    METAL_BARRIER = 64
    TARMAC_MEDIUM_CLEAN_DRY = 65
    TARMAC_MEDIUM_CLEAN_DAMP = 66
    TARMAC_MEDIUM_CLEAN_WET = 67
    TARMAC_COARSE_CLEAN_DRY = 69
    TARMAC_COARSE_CLEAN_DAMP = 70
    TARMAC_COARSE_CLEAN_WET = 71
    TARMAC_MEDIUM_SPRINKLED_DRY = 73
    TARMAC_MEDIUM_SPRINKLED_DAMP = 74
    TARMAC_MEDIUM_SPRINKLED_WET = 75
    TARMAC_COARSE_SPRINKLED_DRY = 77
    TARMAC_COARSE_SPRINKLED_DAMP = 78
    TARMAC_COARSE_SPRINKLED_WET = 79
    TARMAC_MEDIUM_COVERED_DRY = 81
    TARMAC_MEDIUM_COVERED_DAMP = 82
    TARMAC_MEDIUM_COVERED_WET = 83
    TARMAC_COARSE_COVERED_DRY = 85
    TARMAC_COARSE_COVERED_DAMP = 86
    TARMAC_COARSE_COVERED_WET = 87
    SNOWWALL_BOTTOM = 88  # Possibly used on the ground beneath the snowwall object
    COBBLE_DRY = 89
    COBBLE_DAMP = 90
    COBBLE_WET = 91
    SETT_DRY = 92
    SETT_DAMP = 93
    SETT_WET = 94
    GRASS_HARD_DRY = 97
    GRASS_HARD_DAMP = 98
    GRASS_HARD_WET = 99
    SNOWONGRAVEL_SHALLOW = 101
    SNOWONGRAVEL_MEDIUM = 102
    SNOWONGRAVEL_DEEP = 103
    GRASS_MEDIUM_DRY = 105
    GRASS_MEDIUM_DAMP = 106
    GRASS_MEDIUM_WET = 107
    GRASS_SOFT_DRY = 113
    GRASS_SOFT_DAMP = 114
    GRASS_SOFT_WET = 115
    BLACK_ICE = 116
    SNOWONICE_SHALLOW = 117
    SNOWONICE_MEDIUM = 118
    SNOWONICE_DEEP = 119
    TREE_STUMP = 120
    BENDABLE_TREE = 121
    ROUGH_ROUGH_DRY = 129
    ROUGH_ROUGH_WET = 130
    ROUGH_ROUGH_DAMP = 131
    DIRT_HARD_DRY = 133
    DIRT_HARD_DAMP = 134
    DIRT_HARD_WET = 135
    ROUGH_VERYROUGH_DAMP = 136
    ROUGH_VERYROUGH_DRY = 137
    ROUGH_VERYROUGH_WET = 138
    DIRT_MEDIUM_DRY = 141
    DIRT_MEDIUM_DAMP = 142
    DIRT_MEDIUM_WET = 143
    DIRT_SOFT_DRY = 149
    DIRT_SOFT_DAMP = 150
    DIRT_SOFT_WET = 151
    GRAVEL_FINE_SHALLOW_DRY_CLONE = 153
    GRAVEL_FINE_SHALLOW_DAMP_CLONE = 154
    GRAVEL_FINE_SHALLOW_WET_CLONE = 155
    WATER_SURFACE = 157
    DIRT_HARD_DRY_CLONE = 161
    DIRT_HARD_DAMP_CLONE = 162
    DIRT_HARD_WET_CLONE = 163
    VERY_SPARSE_BUSH = 165
    SPARSE_BUSH = 166
    DENSE_BUSH = 167
    VERY_DENSE_BUSH = 168
    US_GRAVEL_FINE_SHALLOW_DRY = 177
    US_GRAVEL_FINE_SHALLOW_DAMP = 178
    US_GRAVEL_FINE_SHALLOW_WET = 179
    BR_GRAVEL_COARSE_SHALLOW_DRY = 181
    BR_GRAVEL_COARSE_SHALLOW_DAMP = 182
    BR_GRAVEL_COARSE_SHALLOW_WET = 183
    US_GRAVEL_FINE_DEEP_DRY = 185
    US_GRAVEL_FINE_DEEP_DAMP = 186
    US_GRAVEL_FINE_DEEP_WET = 187
    BR_GRAVEL_COARSE_DEEP_DRY = 189
    BR_GRAVEL_COARSE_DEEP_DAMP = 190
    BR_GRAVEL_COARSE_DEEP_WET = 191
    US_GRAVEL_FINE_DEEPER_DRY = 193
    US_GRAVEL_FINE_DEEPER_DAMP = 194
    US_GRAVEL_FINE_DEEPER_WET = 195
    BR_GRAVEL_COARSE_DEEPER_DRY = 197
    BR_GRAVEL_COARSE_DEEPER_DAMP = 198
    BR_GRAVEL_COARSE_DEEPER_WET = 199
    SCRIPT_CHARACTER = 200
    PASSTHROUGH = 254
    SPECTATOR = 255

    def simplify(self) -> MaterialId:
        """Turn the clones into non clones"""
        if self is MaterialId.GRAVEL_FINE_SHALLOW_DRY_CLONE:
            return MaterialId.GRAVEL_FINE_SHALLOW_DRY
        elif self is MaterialId.GRAVEL_FINE_SHALLOW_DAMP_CLONE:
            return MaterialId.GRAVEL_FINE_SHALLOW_DAMP
        elif self is MaterialId.GRAVEL_FINE_SHALLOW_WET_CLONE:
            return MaterialId.GRAVEL_FINE_SHALLOW_WET
        elif self is MaterialId.DIRT_HARD_DRY_CLONE:
            return MaterialId.DIRT_HARD_DRY
        elif self is MaterialId.DIRT_HARD_DAMP_CLONE:
            return MaterialId.DIRT_HARD_DAMP
        elif self is MaterialId.DIRT_HARD_WET_CLONE:
            return MaterialId.DIRT_HARD_WET
        return self

    def wetter(self, steps: int) -> MaterialId:
        """Step the wetness up, capped at wet. Materials without a wetness are
        unchanged."""
        parts = self.name.split("_")
        for i, part in enumerate(parts):
            if part in WETNESS_LEVELS:
                level = min(WETNESS_LEVELS.index(part) + steps, len(WETNESS_LEVELS) - 1)
                parts[i] = WETNESS_LEVELS[level]
                return MaterialId["_".join(parts)]
        return self

    def pretty(self) -> str:
        return self.name.replace("_", " ").title()


WETNESS_LEVELS = ("DRY", "DAMP", "WET")


@dataclass
class RGB:
    r: int
    g: int
    b: int


def material_id_to_color(m: MaterialId) -> RGB:
    if m is MaterialId.UNDEFINED:
        return RGB(255, 255, 255)
    if m is MaterialId.GRAVEL_FINE_DEEPER_DRY:
        return RGB(255, 85, 0)
    if m is MaterialId.GRAVEL_FINE_DEEPER_DAMP:
        return RGB(221, 51, 0)
    if m is MaterialId.GRAVEL_FINE_DEEPER_WET:
        return RGB(195, 25, 0)
    if m is MaterialId.GRAVEL_MEDIUM_DEEPER_DRY:
        return RGB(255, 0, 0)
    if m is MaterialId.GRAVEL_MEDIUM_DEEPER_DAMP:
        return RGB(205, 0, 0)
    if m is MaterialId.GRAVEL_MEDIUM_DEEPER_WET:
        return RGB(151, 0, 0)
    if m is MaterialId.GRAVEL_FINE_DEEP_DRY:
        return RGB(218, 97, 37)
    if m is MaterialId.GRAVEL_FINE_DEEP_DAMP:
        return RGB(189, 68, 32)
    if m is MaterialId.GRAVEL_FINE_DEEP_WET:
        return RGB(167, 46, 28)
    if m is MaterialId.GRAVEL_MEDIUM_DEEP_DRY:
        return RGB(218, 37, 37)
    if m is MaterialId.GRAVEL_MEDIUM_DEEP_DAMP:
        return RGB(175, 29, 29)
    if m is MaterialId.GRAVEL_MEDIUM_DEEP_WET:
        return RGB(129, 22, 22)
    if m is MaterialId.GRAVEL_FINE_SHALLOW_DRY:
        return RGB(190, 106, 64)
    if m is MaterialId.GRAVEL_FINE_SHALLOW_DAMP:
        return RGB(165, 81, 56)
    if m is MaterialId.GRAVEL_FINE_SHALLOW_WET:
        return RGB(145, 61, 49)
    if m is MaterialId.GRAVEL_MEDIUM_SHALLOW_DRY:
        return RGB(190, 64, 64)
    if m is MaterialId.GRAVEL_MEDIUM_SHALLOW_DAMP:
        return RGB(153, 52, 52)
    if m is MaterialId.GRAVEL_MEDIUM_SHALLOW_WET:
        return RGB(112, 38, 38)
    if m is MaterialId.SPRET_BUSH_SMALL:
        return RGB(255, 255, 255)
    if m is MaterialId.SPRET_BUSH_MEDIUM:
        return RGB(255, 255, 255)
    if m is MaterialId.SPRET_BUSH_LARGE:
        return RGB(255, 255, 255)
    if m is MaterialId.LOV_BUSH_SMALL:
        return RGB(255, 255, 255)
    if m is MaterialId.LOV_BUSH_MEDIUM:
        return RGB(255, 255, 255)
    if m is MaterialId.LOV_BUSH_LARGE:
        return RGB(255, 255, 255)
    if m is MaterialId.TREE_SMALL:
        return RGB(255, 255, 255)
    if m is MaterialId.TREE_MEDIUM:
        return RGB(255, 255, 255)
    if m is MaterialId.TREE_LARGE:
        return RGB(255, 255, 255)
    if m is MaterialId.GRAVEL_COARSE_DEEPER_DRY:
        return RGB(255, 0, 85)
    if m is MaterialId.GRAVEL_COARSE_DEEPER_DAMP:
        return RGB(200, 0, 30)
    if m is MaterialId.GRAVEL_COARSE_DEEPER_WET:
        return RGB(183, 24, 24)
    if m is MaterialId.TARMAC_FINE_CLEAN_DRY:
        return RGB(0, 211, 255)
    if m is MaterialId.TARMAC_FINE_CLEAN_DAMP:
        return RGB(0, 180, 224)
    if m is MaterialId.TARMAC_FINE_CLEAN_WET:
        return RGB(0, 136, 180)
    if m is MaterialId.GRAVEL_COARSE_DEEP_DRY:
        return RGB(218, 37, 97)
    if m is MaterialId.GRAVEL_COARSE_DEEP_DAMP:
        return RGB(171, 29, 50)
    if m is MaterialId.GRAVEL_COARSE_DEEP_WET:
        return RGB(143, 24, 24)
    if m is MaterialId.TARMAC_FINE_SPRINKLED_DRY:
        return RGB(52, 176, 203)
    if m is MaterialId.TARMAC_FINE_SPRINKLED_DAMP:
        return RGB(45, 152, 178)
    if m is MaterialId.TARMAC_FINE_SPRINKLED_WET:
        return RGB(36, 117, 143)
    if m is MaterialId.GRAVEL_COARSE_SHALLOW_DRY:
        return RGB(190, 64, 106)
    if m is MaterialId.GRAVEL_COARSE_SHALLOW_DAMP:
        return RGB(149, 51, 66)
    if m is MaterialId.GRAVEL_COARSE_SHALLOW_WET:
        return RGB(124, 42, 42)
    if m is MaterialId.TARMAC_FINE_COVERED_DRY:
        return RGB(77, 159, 177)
    if m is MaterialId.TARMAC_FINE_COVERED_DAMP:
        return RGB(68, 138, 155)
    if m is MaterialId.TARMAC_FINE_COVERED_WET:
        return RGB(55, 108, 125)
    if m is MaterialId.ROCK_SMALL:
        return RGB(255, 255, 255)
    if m is MaterialId.ROCK_MEDIUM:
        return RGB(255, 255, 255)
    if m is MaterialId.ROCK_LARGE:
        return RGB(255, 255, 255)
    if m is MaterialId.TRUNK_SMALL:
        return RGB(255, 255, 255)
    if m is MaterialId.TRUNK_MEDIUM:
        return RGB(255, 255, 255)
    if m is MaterialId.TRUNK_LARGE:
        return RGB(255, 255, 255)
    if m is MaterialId.SNOWWALL:
        return RGB(255, 255, 255)
    if m is MaterialId.METAL_POLE:
        return RGB(255, 255, 255)
    if m is MaterialId.METAL_BARRIER:
        return RGB(255, 255, 255)
    if m is MaterialId.TARMAC_MEDIUM_CLEAN_DRY:
        return RGB(0, 0, 255)
    if m is MaterialId.TARMAC_MEDIUM_CLEAN_DAMP:
        return RGB(0, 0, 206)
    if m is MaterialId.TARMAC_MEDIUM_CLEAN_WET:
        return RGB(0, 0, 155)
    if m is MaterialId.TARMAC_COARSE_CLEAN_DRY:
        return RGB(182, 0, 255)
    if m is MaterialId.TARMAC_COARSE_CLEAN_DAMP:
        return RGB(141, 0, 200)
    if m is MaterialId.TARMAC_COARSE_CLEAN_WET:
        return RGB(92, 0, 136)
    if m is MaterialId.TARMAC_MEDIUM_SPRINKLED_DRY:
        return RGB(52, 52, 203)
    if m is MaterialId.TARMAC_MEDIUM_SPRINKLED_DAMP:
        return RGB(42, 42, 164)
    if m is MaterialId.TARMAC_MEDIUM_SPRINKLED_WET:
        return RGB(31, 31, 123)
    if m is MaterialId.TARMAC_COARSE_SPRINKLED_DRY:
        return RGB(160, 52, 203)
    if m is MaterialId.TARMAC_COARSE_SPRINKLED_DAMP:
        return RGB(123, 36, 158)
    if m is MaterialId.TARMAC_COARSE_SPRINKLED_WET:
        return RGB(78, 12, 104)
    if m is MaterialId.TARMAC_MEDIUM_COVERED_DRY:
        return RGB(77, 77, 177)
    if m is MaterialId.TARMAC_MEDIUM_COVERED_DAMP:
        return RGB(63, 63, 143)
    if m is MaterialId.TARMAC_MEDIUM_COVERED_WET:
        return RGB(47, 47, 108)
    if m is MaterialId.TARMAC_COARSE_COVERED_DRY:
        return RGB(129, 84, 148)
    if m is MaterialId.TARMAC_COARSE_COVERED_DAMP:
        return RGB(98, 62, 113)
    if m is MaterialId.TARMAC_COARSE_COVERED_WET:
        return RGB(59, 31, 70)
    if m is MaterialId.COBBLE_DRY:
        return RGB(180, 40, 220)
    if m is MaterialId.COBBLE_DAMP:
        return RGB(160, 20, 200)
    if m is MaterialId.COBBLE_WET:
        return RGB(140, 0, 180)
    if m is MaterialId.SETT_DRY:
        return RGB(180, 220, 40)
    if m is MaterialId.SETT_DAMP:
        return RGB(160, 200, 20)
    if m is MaterialId.SETT_WET:
        return RGB(140, 180, 0)
    if m is MaterialId.SNOWWALL_BOTTOM:
        return RGB(255, 255, 255)
    if m is MaterialId.GRASS_HARD_DRY:
        return RGB(0, 255, 76)
    if m is MaterialId.GRASS_HARD_DAMP:
        return RGB(0, 217, 90)
    if m is MaterialId.GRASS_HARD_WET:
        return RGB(0, 165, 68)
    if m is MaterialId.SNOWONGRAVEL_SHALLOW:
        return RGB(255, 252, 0)
    if m is MaterialId.SNOWONGRAVEL_MEDIUM:
        return RGB(203, 201, 52)
    if m is MaterialId.SNOWONGRAVEL_DEEP:
        return RGB(163, 162, 91)
    if m is MaterialId.GRASS_MEDIUM_DRY:
        return RGB(47, 208, 95)
    if m is MaterialId.GRASS_MEDIUM_DAMP:
        return RGB(40, 177, 97)
    if m is MaterialId.GRASS_MEDIUM_WET:
        return RGB(30, 134, 73)
    if m is MaterialId.GRASS_SOFT_DRY:
        return RGB(87, 167, 111)
    if m is MaterialId.GRASS_SOFT_DAMP:
        return RGB(74, 142, 102)
    if m is MaterialId.GRASS_SOFT_WET:
        return RGB(56, 108, 78)
    if m is MaterialId.BLACK_ICE:
        return RGB(159, 159, 159)
    if m is MaterialId.SNOWONICE_SHALLOW:
        return RGB(159, 255, 0)
    if m is MaterialId.SNOWONICE_MEDIUM:
        return RGB(147, 208, 47)
    if m is MaterialId.SNOWONICE_DEEP:
        return RGB(138, 174, 79)
    if m is MaterialId.TREE_STUMP:
        return RGB(255, 255, 255)
    if m is MaterialId.BENDABLE_TREE:
        return RGB(255, 255, 255)
    if m is MaterialId.ROUGH_ROUGH_DRY:
        return RGB(255, 0, 255)
    if m is MaterialId.ROUGH_ROUGH_WET:
        return RGB(168, 0, 168)
    if m is MaterialId.ROUGH_ROUGH_DAMP:
        return RGB(200, 0, 200)
    if m is MaterialId.DIRT_HARD_DRY:
        return RGB(255, 168, 0)
    if m is MaterialId.DIRT_HARD_DAMP:
        return RGB(209, 122, 0)
    if m is MaterialId.DIRT_HARD_WET:
        return RGB(158, 71, 0)
    if m is MaterialId.ROUGH_VERYROUGH_DRY:
        return RGB(199, 56, 198)
    if m is MaterialId.ROUGH_VERYROUGH_WET:
        return RGB(131, 37, 131)
    if m is MaterialId.ROUGH_VERYROUGH_DAMP:
        return RGB(170, 45, 160)
    if m is MaterialId.DIRT_MEDIUM_DRY:
        return RGB(183, 145, 72)
    if m is MaterialId.DIRT_MEDIUM_DAMP:
        return RGB(150, 112, 59)
    if m is MaterialId.DIRT_MEDIUM_WET:
        return RGB(113, 75, 44)
    if m is MaterialId.DIRT_SOFT_DRY:
        return RGB(155, 136, 100)
    if m is MaterialId.DIRT_SOFT_DAMP:
        return RGB(127, 108, 82)
    if m is MaterialId.DIRT_SOFT_WET:
        return RGB(95, 76, 61)
    if m is MaterialId.GRAVEL_FINE_SHALLOW_DRY_CLONE:
        return RGB(215, 215, 175)
    if m is MaterialId.GRAVEL_FINE_SHALLOW_DAMP_CLONE:
        return RGB(183, 183, 149)
    if m is MaterialId.GRAVEL_FINE_SHALLOW_WET_CLONE:
        return RGB(145, 145, 118)
    if m is MaterialId.WATER_SURFACE:
        return RGB(0, 0, 175)
    if m is MaterialId.DIRT_HARD_DRY_CLONE:
        return RGB(186, 186, 123)
    if m is MaterialId.DIRT_HARD_DAMP_CLONE:
        return RGB(159, 159, 104)
    if m is MaterialId.DIRT_HARD_WET_CLONE:
        return RGB(126, 126, 81)
    if m is MaterialId.VERY_SPARSE_BUSH:
        return RGB(220, 220, 220)
    if m is MaterialId.SPARSE_BUSH:
        return RGB(175, 175, 175)
    if m is MaterialId.DENSE_BUSH:
        return RGB(100, 100, 100)
    if m is MaterialId.VERY_DENSE_BUSH:
        return RGB(255, 255, 255)
    if m is MaterialId.US_GRAVEL_FINE_SHALLOW_DRY:
        return RGB(190, 106, 64)
    if m is MaterialId.US_GRAVEL_FINE_SHALLOW_DAMP:
        return RGB(165, 81, 56)
    if m is MaterialId.US_GRAVEL_FINE_SHALLOW_WET:
        return RGB(145, 61, 49)
    if m is MaterialId.BR_GRAVEL_COARSE_SHALLOW_DRY:
        return RGB(190, 146, 64)
    if m is MaterialId.BR_GRAVEL_COARSE_SHALLOW_DAMP:
        return RGB(165, 121, 56)
    if m is MaterialId.BR_GRAVEL_COARSE_SHALLOW_WET:
        return RGB(145, 101, 49)
    if m is MaterialId.US_GRAVEL_FINE_DEEP_DRY:
        return RGB(210, 106, 64)
    if m is MaterialId.US_GRAVEL_FINE_DEEP_DAMP:
        return RGB(185, 81, 56)
    if m is MaterialId.US_GRAVEL_FINE_DEEP_WET:
        return RGB(165, 61, 49)
    if m is MaterialId.BR_GRAVEL_COARSE_DEEP_DRY:
        return RGB(210, 146, 64)
    if m is MaterialId.BR_GRAVEL_COARSE_DEEP_DAMP:
        return RGB(185, 121, 56)
    if m is MaterialId.BR_GRAVEL_COARSE_DEEP_WET:
        return RGB(165, 101, 49)
    if m is MaterialId.US_GRAVEL_FINE_DEEPER_DRY:
        return RGB(230, 146, 64)
    if m is MaterialId.US_GRAVEL_FINE_DEEPER_DAMP:
        return RGB(205, 121, 56)
    if m is MaterialId.US_GRAVEL_FINE_DEEPER_WET:
        return RGB(185, 101, 49)
    if m is MaterialId.BR_GRAVEL_COARSE_DEEPER_DRY:
        return RGB(230, 146, 64)
    if m is MaterialId.BR_GRAVEL_COARSE_DEEPER_DAMP:
        return RGB(205, 121, 56)
    if m is MaterialId.BR_GRAVEL_COARSE_DEEPER_WET:
        return RGB(185, 101, 49)
    if m is MaterialId.PASSTHROUGH:
        return RGB(100, 100, 100)
    if m is MaterialId.SPECTATOR:
        return RGB(0, 0, 255)
    return RGB(255, 255, 255)


@dataclass
class MaterialMap:
    bitmap: List[List[MaterialId]]

    def __hash__(self) -> int:
        return hash(tuple([m for row in self.bitmap for m in row]))

    @staticmethod
    def full(m: MaterialId) -> MaterialMap:
        bitmap = []
        for row in range(16):
            cols = []
            for col in range(16):
                cols.append(m)
            bitmap.append(cols)
        return MaterialMap(bitmap)

    def copy_x(self) -> MaterialMap:
        """Swap the left and right halves of the map.

        1 2  ->  2 1
        3 4      4 3
        """
        rows: List[List[MaterialId]] = []
        for row in self.bitmap:
            left = row[:8]
            right = row[8:]
            rows.append(right + left)
        return MaterialMap(bitmap=rows)

    def copy_y(self) -> MaterialMap:
        """Swap the top and bottom halves of the map.

        1 2  ->  3 4
        3 4      1 2
        """
        top = self.bitmap[:8]
        bottom = self.bitmap[8:]
        rows = bottom + top
        return MaterialMap(bitmap=rows)

    def copy_xy(self) -> MaterialMap:
        """A combination of copy_x and copy_y"""
        return self.copy_x().copy_y()


def pretty_enum(e: enum.Enum) -> str:
    return e.name[:1] + e.name[1:].lower()


class TimeOfDay(str, enum.Enum):
    MORNING = "M"
    NOON = "N"
    EVENING = "E"

    def pretty(self) -> str:
        return self.name.title()

    def to_tint_set(self) -> TintSet:
        if self is TimeOfDay.MORNING:
            return TintSet.MORNING
        elif self is TimeOfDay.NOON:
            return TintSet.NOON
        elif self is TimeOfDay.EVENING:
            return TintSet.EVENING
        else:
            raise NotImplementedError


class Weather(str, enum.Enum):
    CRISP = "crisp"
    HAZY = "hazy"
    LIGHT_FOG = "lightfog"
    HEAVY_FOG = "heavyfog"
    NO_RAIN = "norain"
    LIGHT_RAIN = "lightrain"
    HEAVY_RAIN = "heavyrain"
    NO_SNOW = "nosnow"
    LIGHT_SNOW = "lightsnow"
    HEAVY_SNOW = "heavysnow"

    def pretty(self) -> str:
        return " ".join(self.name.split("_")).title()

    def id(self) -> int:
        if self is Weather.CRISP:
            return 0
        elif self is Weather.HAZY:
            return 1
        elif self is Weather.LIGHT_FOG:
            return 2
        elif self is Weather.HEAVY_FOG:
            return 3
        elif self is Weather.NO_RAIN:
            return 4
        elif self is Weather.LIGHT_RAIN:
            return 5
        elif self is Weather.HEAVY_RAIN:
            return 6
        elif self is Weather.NO_SNOW:
            return 7
        elif self is Weather.LIGHT_SNOW:
            return 8
        elif self is Weather.HEAVY_SNOW:
            return 9
        assert_never(self)


class Sky(str, enum.Enum):
    CLEAR = "clear"
    PART_CLOUD = "partcloud"
    LIGHT_CLOUD = "lightcloud"
    HEAVY_CLOUD = "heavycloud"

    def pretty(self) -> str:
        return " ".join(self.name.split("_")).title()

    def id(self) -> int:
        if self is Sky.CLEAR:
            return 0
        elif self is Sky.PART_CLOUD:
            return 1
        elif self is Sky.LIGHT_CLOUD:
            return 2
        elif self is Sky.HEAVY_CLOUD:
            return 3
        assert_never(self)


class CloudName(str, enum.Enum):
    CLEAR = "Us_clear"
    CLEAR02 = "Us_clear02"
    CLOUDED = "Us_clouded"
    CLOUDED02 = "Us_clouded02"
    OVERCAST = "Us_overcast"
    OVERCAST02 = "Us_overcast02"
    PARTLY_CLOUDED = "Us_partly_clouded"
    PARTLY_CLOUDED02 = "Us_partly_clouded02"
    PRECIPITATION = "Us_precipitation"
    PRECIPITATION_PC = "Us_precipitation_pc"
    PRECIPITATION02_PC = "Us_precipitation02_pc"

    def pretty(self) -> str:
        return self.name.replace("_", " ").title()

    def id(self) -> int:
        # Be careful when changing this, blend files use it.
        return list(CloudName).index(self)

    def texture_name(self) -> str:
        if self is CloudName.CLEAR:
            return "US_CLEAR"
        elif self is CloudName.CLEAR02:
            return "US_CLEAR02"
        elif self is CloudName.CLOUDED:
            return "US_CLOUDED"
        elif self is CloudName.CLOUDED02:
            return "US_CLOUDED"
        elif self is CloudName.OVERCAST:
            return "US_OVERCAST"
        elif self is CloudName.OVERCAST02:
            return "US_OVERCAST"
        elif self is CloudName.PARTLY_CLOUDED:
            return "US_PARTLY_CLOUDED"
        elif self is CloudName.PARTLY_CLOUDED02:
            return "US_PARTLY_CLOUDED"
        elif self is CloudName.PRECIPITATION:
            return "US_PRECIPITATION"
        elif self is CloudName.PRECIPITATION_PC:
            return "US_PRECIPITATION_PC"
        elif self is CloudName.PRECIPITATION02_PC:
            return "US_PRECIPITATION_PC"
        else:
            raise NotImplementedError(f"Missing case in CloudName.texture_name: {self}")


class SurfaceType(enum.Enum):
    DRY = 0x0
    DAMP = 0x1
    WET = 0x2

    def pretty(self) -> str:
        return pretty_enum(self)

    def description(self) -> str:
        return self.pretty()

    def bitmask(self) -> int:
        if self is SurfaceType.DRY:
            return 0b001
        elif self is SurfaceType.DAMP:
            return 0b010
        elif self is SurfaceType.WET:
            return 0b100
        assert_never(self)

    @staticmethod
    def from_string(string: str) -> Optional[SurfaceType]:
        for t in SurfaceType:
            if t.to_string() in string:
                return t
        return None

    def to_string(self) -> str:
        return self.name.lower()


class SurfaceAge(enum.Enum):
    NEW = 0x0
    NORMAL = 0x1
    WORN = 0x2

    def pretty(self) -> str:
        return pretty_enum(self)

    def description(self) -> str:
        return self.pretty()

    @staticmethod
    def from_string(string: str) -> Optional[SurfaceAge]:
        for t in SurfaceAge:
            if t.to_string() in string:
                return t
        return None

    def to_string(self) -> str:
        return self.name.lower()


@dataclass
class ConditionIdentifier:
    surface_type: SurfaceType
    surface_age: SurfaceAge
    name: str = ""

    def __hash__(self) -> int:
        return (self.surface_type.value, self.surface_age.value).__hash__()

    def packed_index(self) -> int:
        return 3 * self.surface_type.value + self.surface_age.value


_ByConditionValue = TypeVar("_ByConditionValue")


def by_condition(
    value: Callable[[SurfaceType, SurfaceAge], _ByConditionValue],
) -> dict[str, dict[str, _ByConditionValue]]:
    return {
        surface.name.lower(): {
            age.name.lower(): value(surface, age) for age in SurfaceAge
        }
        for surface in SurfaceType
    }


# RBR has limits on how complex the collision meshes can be.
MAX_SCM_VERTICES = 30
MAX_SCM_EDGES = 84
MAX_SCM_FACES = 56


class TintSet(str, enum.Enum):
    MORNING = "M"
    NOON = "N"
    EVENING = "E"
    OVERCAST = "O"

    def pretty(self) -> str:
        return self.name.title()

    def bitmask(self) -> int:
        if self is TintSet.MORNING:
            return 0b00001
        elif self is TintSet.NOON:
            return 0b00010
        elif self is TintSet.EVENING:
            return 0b00100
        elif self is TintSet.OVERCAST:
            return 0b01000
        else:
            raise NotImplementedError

    def shader_value(self) -> int:
        if self is TintSet.MORNING:
            return 0
        elif self is TintSet.NOON:
            return 1
        elif self is TintSet.EVENING:
            return 2
        elif self is TintSet.OVERCAST:
            return 3
        else:
            raise NotImplementedError

    def to_time_of_day(self) -> Optional[TimeOfDay]:
        if self is TintSet.MORNING:
            return TimeOfDay.MORNING
        elif self is TintSet.NOON:
            return TimeOfDay.NOON
        elif self is TintSet.EVENING:
            return TimeOfDay.EVENING
        else:
            return None


class RBRMeshMaterialType(enum.Enum):
    GEOM_BLOCK = 0x0
    OBJECT_BLOCK = 0x1
    REFLECTION_OBJECT = 0x2
    WATER_OBJECT = 0x3
    SUPER_BOWL = 0x4
    INTERACTIVE_OBJECT_VISUAL = 0x5
    CLIPPING_PLANE = 0x6

    def pretty(self) -> str:
        return self.name.replace("_", " ").title()

    def description(self) -> str:
        return self.pretty()


class GeomBlockType(enum.Enum):
    NEAR = 0x0
    FAR = 0x1
    ANY = 0x2

    def pretty(self) -> str:
        return self.name.replace("_", " ").title()

    def description(self) -> str:
        if self is GeomBlockType.NEAR:
            return "Mesh is visible within 600m (high resolution mesh, used to generate collision mesh)"
        elif self is GeomBlockType.ANY:
            return "Mesh is visible from any distance (mid-low resolution mesh)"
        elif self is GeomBlockType.FAR:
            return "Mesh is not visible within 550m (very low resolution version of 'Near' mesh)"
        assert_never(self)


class ObjectBlockType(enum.Enum):
    NEAR = 0x0
    FAR = 0x1
    BOTH = 0x2

    def pretty(self) -> str:
        return self.name.replace("_", " ").title()

    def description(self) -> str:
        if self is ObjectBlockType.NEAR:
            return "Only visible when within 1500m"
        elif self is ObjectBlockType.FAR:
            return "Only visible when over 1500m away"
        elif self is ObjectBlockType.BOTH:
            return "Always visible"
        assert_never(self)


class StageSurface(enum.Enum):
    TARMAC = 0
    GRAVEL = 1
    SNOW = 2

    def pretty(self) -> str:
        return self.name.title()

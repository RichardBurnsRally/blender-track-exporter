from . import brake_wall
from . import car_location
from . import driveline
from . import fence_modifier
from . import registration_zone
from . import sun_direction


def register() -> None:
    brake_wall.register()
    car_location.register()
    driveline.register()
    fence_modifier.register()
    registration_zone.register()
    sun_direction.register()


def unregister() -> None:
    sun_direction.unregister()
    registration_zone.unregister()
    fence_modifier.unregister()
    driveline.unregister()
    car_location.unregister()
    brake_wall.unregister()

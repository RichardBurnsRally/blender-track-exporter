from . import camera
from . import collision
from . import curve
from . import fence
from . import mesh
from . import object
from . import scene
from . import world


def register() -> None:
    collision.register()
    fence.register()
    object.register()
    camera.register()
    curve.register()
    mesh.register()
    world.register()
    scene.register()


def unregister() -> None:
    scene.unregister()
    world.unregister()
    mesh.unregister()
    curve.unregister()
    camera.unregister()
    object.unregister()
    fence.unregister()
    collision.unregister()

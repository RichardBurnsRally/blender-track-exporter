from . import object
from . import scene
from . import world


def register() -> None:
    object.register()
    scene.register()
    world.register()


def unregister() -> None:
    world.unregister()
    scene.unregister()
    object.unregister()

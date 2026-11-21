from . import driveline


def register() -> None:
    driveline.register()


def unregister() -> None:
    driveline.unregister()

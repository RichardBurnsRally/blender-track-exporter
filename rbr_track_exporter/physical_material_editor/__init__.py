from . import operator
from . import panel
from . import properties


def register() -> None:
    properties.register()
    operator.register()
    panel.register()


def unregister() -> None:
    panel.unregister()
    operator.unregister()
    properties.unregister()

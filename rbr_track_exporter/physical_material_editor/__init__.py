from . import editor
from . import ops
from . import panel
from . import properties
from . import tools


def register() -> None:
    properties.register()
    editor.register()
    ops.register()
    tools.register()
    panel.register()


def unregister() -> None:
    panel.unregister()
    tools.unregister()
    ops.unregister()
    editor.unregister()
    properties.unregister()

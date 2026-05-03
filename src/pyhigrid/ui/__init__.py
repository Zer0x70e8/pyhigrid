#
""""""

from pyhigrid.configue import UI_ENUM

def import_ui(ui: UI_ENUM):
    match ui:
        # case UI_ENUM.CLI:
        #     import .
        #     return None
        # case UI_ENUM.TUI:
        #     import .
        #     return app
        case UI_ENUM.GUI:
            from .gui import Application as App
            return App
        case _:
            raise RuntimeError(f"[UI] Not found: {ui.value}.")


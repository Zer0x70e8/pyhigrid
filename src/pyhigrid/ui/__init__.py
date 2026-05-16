#
""""""

from .ui_enum import UI

def import_ui(ui: UI):
    match ui:
        # case UI.CLI:
        #     import .
        #     return None
        # case UI.TUI:
        #     import .
        #     return app
        case UI.GUI:
            from .gui import Application as App
            return App
        case _:
            raise RuntimeError(f"[UI] Not found: {ui.value}.")


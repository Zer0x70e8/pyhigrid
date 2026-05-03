#
""""""

class Application:
    def __init__(self, bg=None, ui=None, logger=None, configurator=None):
        self.bg = bg
        self.ui = ui
        self.logger = logger
        self.configurator = configurator

    def setup(self, bg=None, ui=None, logger=None, configurator=None):
        if bg is not None:
            self.bg = bg
        if ui is not None:
            self.ui = ui
        if logger is not None:
            self.logger = logger
        if configurator is not None:
            self.configurator = configurator

    def check(self) -> bool:
        if None in (self.bg, self.ui, self.logger):
            return False
        return True

    def exec(self):
        if not self.check():
            missing = []
            if self.bg is None:
                missing.append("bg")
            if self.ui is None:
                missing.append("ui")
            if self.logger is None:
                missing.append("logger")
            raise RuntimeError(f"Missing application: {', '.join(missing)}")
        self.logger.debug("Executing application.")

        # self.bg.run()
        ui_end_code = self.ui.exec()

        self.logger.debug("The core program is closing now.")
        return (
            # self.bg.end_code,
            ui_end_code
        )




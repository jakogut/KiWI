class Menu(object):
    def __init__(self, dialog, items, title, caller = None):
        self.d = dialog
        self.caller = caller

        self.entries = []
        self.dispatch_table = {}
        tag = 1

        self.title = title

        for entry, func in items:
            self.entries.append(tuple([str(tag), entry]))
            self.dispatch_table[str(tag)] = func
            tag += 1

    def run(self, ret=None):
        code, tag = self.d.menu(self.title, choices=self.entries)
        if code == self.d.OK: self.dispatch(tag)
        if ret: ret()

    def dispatch(self, tag):
        if tag in self.dispatch_table:
            func = self.dispatch_table[tag]
            if isinstance(func, Menu):
                func.run(ret=self.run)
            else: func()


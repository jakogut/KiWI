class MenuItem(object):
    def __init__(self, func=None):
        if func: self.function = func

    # Wrapper for child.function() that creates a call stack
    def run(self, ret=None):
        self.function()
        if ret: ret()

class Menu(MenuItem):
    def __init__(self, dialog, items, title):
        self.d = dialog

        self.entries = []
        self.dispatch_table = {}
        tag = 1

        self.title = title

        for entry, func in items:
            self.entries.append(tuple([str(tag), entry]))
            self.dispatch_table[str(tag)] = func
            tag += 1

    def function(self):
        code, tag = self.d.menu(self.title, choices=self.entries)
        if code == self.d.OK: self._dispatch(tag)

    def _dispatch(self, tag):
        if tag in self.dispatch_table:
            func = self.dispatch_table[tag]
            if isinstance(func, MenuItem):
                func.run(ret=self.run)
            else: func()

class StatefulMenu(Menu):
    def __init__(self, dialog, items, title, position=0):
        super().__init__(dialog, items, title)
        self.position = position

    def advance(self):
        self.position += 1

    def function(self):
        code, tag = self.d.menu(self.title, choices=self.entries,
            default_item=self.entries[self.position][0])

        if code == self.d.OK: self._dispatch(tag)

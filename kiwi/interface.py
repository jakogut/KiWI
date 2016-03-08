separator_tag = '*'

class MenuItem(object):
    def __init__(self, func=None, separator=False):
        self.function = func
        self.separator = separator

    # Wrapper for child.function() that creates a call stack
    def run(self, ret=None):
        if self.function: self.function()
        if ret: ret()

class Menu(MenuItem):
    def __init__(self, dialog, items, title):
        self.d = dialog

        super().__init__(func=self.function)

        self.entries = []
        self.dispatch_table = {}
        tag = 1

        self.title = title

        for entry, item in items:
            if isinstance(item, MenuItem) and item.separator is True:
                self.entries.append(tuple([separator_tag, entry]))
            else:
                self.entries.append(tuple([str(tag), entry]))
                self.dispatch_table[str(tag)] = item
                tag += 1

    def function(self):
        code, tag = self.d.menu(self.title, choices=self.entries)
        if code == self.d.OK: self._dispatch(tag)

    def _dispatch(self, tag):
        if tag == separator_tag: self.run()
        elif tag in self.dispatch_table:
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

import ast
from contextlib import contextmanager

import astor


class NbCell:
    def __init__(self, cell_type, metadata=None):
        self.cell_type = cell_type
        self.metadata = metadata or {}
        self.source = []

    def add_node(self, node):
        raise NotImplementedError

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class NbCodeCell(NbCell):
    def __init__(self, metadata=None):
        super().__init__("code", metadata)
        self.outputs = []

    def add_node(self, node):
        source = astor.to_source(node)
        self.source.extend([line + "\n" for line in source.split("\n")])


class NbMarkdownCell(NbCell):
    def __init__(self, metadata=None):
        super().__init__("markdown", metadata)

    def add_node(self, node):
        child = node.value
        if not (isinstance(child, ast.Constant) and isinstance(child.value, str)):
            raise TypeError("MarkdownCell can only contain string")
        self.source.append(child.value.format(**get_context()))


def nb_markdown_cell(**metadata):
    return NbMarkdownCell(metadata)


def nb_code_cell(**metadata):
    return NbCodeCell(metadata)


def get_variable(key, default=None):
    return __context.get(key, default)


def set_variable(key, value):
    __context[key] = value


def get_context():
    return __context


__context = {}

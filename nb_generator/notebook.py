import ast
import importlib
import json
import os
import pathlib

from .helper import NbCell, NbCodeCell, set_variable


class VM:
    def __init__(self):
        self.namespace = {}

    def set_variable(self, key, value):
        self.namespace[key] = value

    def get_variable(self, key):
        return self.namespace[key]

    def _run_node(self, node):
        name = type(node).__name__
        handler = getattr(self, f"_run_{name}", None)
        if handler is not None:
            return handler(node)

    def _run_Module(self, node: ast.Module):
        result = []
        for child in node.body:
            item = self._run_node(child)
            if item is not None:
                result.append(item)
        return result

    def _run_Import(self, node: ast.Import):
        for child in node.names:
            self.set_variable(child.asname, importlib.import_module(child.name))

    def _run_ImportFrom(self, node: ast.ImportFrom):
        module = importlib.import_module(node.module)
        for child in node.names:
            asname = child.asname or child.name
            self.set_variable(asname, getattr(module, child.name))

    def _run_With(self, node: ast.With):
        if len(node.items) == 1:
            item = self._run_node(node.items[0].context_expr)
            if isinstance(item, NbCell):
                for child in node.body:
                    item.add_node(child)
                return item

    def _run_Call(self, node: ast.Call):
        function = self._run_node(node.func)
        args = [self._run_node(arg) for arg in node.args]
        kwargs = {key: self._run_node(value) for (key, value) in node.keywords}
        return function(*args, **kwargs)

    def _run_Name(self, node: ast.Name):
        return self.get_variable(node.id)

    def _run_Attribute(self, node: ast.Attribute):
        value = self._run_node(node.value)
        return getattr(value, node.attr)

    def _run_Expr(self, node: ast.Expr):
        return self._run_node(node.value)

    def _run_Constant(self, node: ast.Constant):
        return node.value


class NotebookGenerator:
    def __init__(self, filename, **kwargs):
        self.filename = filename
        self.ctx = kwargs

    def generate(self):
        for key, value in self.ctx.items():
            set_variable(key, value)
        with open(self.filename) as f:
            source = f.read()
        module = ast.parse(source)
        cells = [self._generate_ctx_cell(self.ctx)]
        vm = VM()
        cells.extend(vm._run_node(module))
        notebook_data = self._generate_notebook(cells)
        self.nb_name = pathlib.Path(self.filename).with_suffix(".ipynb")
        with open(self.nb_name, "w") as f:
            json.dump(notebook_data, f)
        return self

    def convert(self, **kwargs):
        cmdline = ["jupyter-nbconvert", str(self.nb_name)]
        for key, value in kwargs.items():
            cmdline.append(f"--{key}")
            if value is not True:
                cmdline.append(f"\"{value}\"")
        os.system(" ".join(cmdline))

    def _generate_ctx_cell(self, ctx):
        source = ["from nb_generator import get_variable, set_variable\n"]
        for key, value in ctx.items():
            source.append("set_variable(\"{}\", {})\n".format(key, repr(value)))
        node = NbCodeCell()
        node.source = source
        return node

    def _generate_notebook(self, cells):
        return {
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3 (ipykernel)",
                    "language": "python",
                    "name": "python3",
                },
            },
            "nbformat": 4,
            "nbformat_minor": 5,
            "cells": [dict(cell.__dict__, execution_count=i) for i, cell in enumerate(cells)],
        }

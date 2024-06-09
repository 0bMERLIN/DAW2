from dataclasses import dataclass
from typing import Callable
from app import onkey, widget, getapp
import pygame as pg


def operation(redo: Callable, undo: Callable):
    "registers an operation that can be undone by `undo`. executes redo immediate"
    redo()
    getapp().find_widget(UndoWidget).stack += [(redo, undo)]


def done_operation(redo: Callable, undo: Callable):
    """registers an operation that can be undone by `undo`.
    assumes the action has already been performed"""
    getapp().find_widget(UndoWidget).stack += [(redo, undo)]


@widget
class UndoWidget:
    stack: list
    "list of the last operations (most recent last)"

    def __init__(self):
        self.stack = []
        self.redo_stack = []

    @onkey(pg.K_UP, pg.KMOD_CTRL)
    def _(self):
        if self.stack != []:
            r, u = self.stack.pop()
            u()
            self.redo_stack += [(r, u)]

    @onkey(pg.K_DOWN, pg.KMOD_CTRL)
    def _(self):
        if self.redo_stack != []:
            r, u = self.redo_stack.pop()
            r()
            self.stack += [(r, u)]

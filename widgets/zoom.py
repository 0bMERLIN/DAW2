from dataclasses import dataclass
from app import onevent, widget
import pygame as pg


@dataclass
@widget
class ZoomWidget:
    """
    Keeps track of zooming.
    Listens to `pg.MOUSEWHEEL`
    """

    zoom: int = 0.05

    @onevent(pg.MOUSEWHEEL)
    def _(self, e):
        zoom_speed = 0.05
        self.zoom *= (1 + zoom_speed) if e.y > 0 else (1 - zoom_speed)

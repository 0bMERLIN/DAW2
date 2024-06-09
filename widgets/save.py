from dataclasses import dataclass
import os
import sys
from app import getapp, onkey, widget
import pygame as pg

from widgets.track import TrackWidget


@dataclass
@widget
class SaveWidget:
    @onkey(pg.K_v, pg.KMOD_CTRL)
    def _(self):
        p = sys.argv[1]
        print(f"saving {p}....")
        os.system("rm " + p + ("" if p.startswith("/") else "/") + "*")
        for t in getapp().find_widgets(TrackWidget):
            t.save(p)

    def load(self):
        p = sys.argv[1]
        print("loading...")
        for t in os.listdir(p):
            if t.startswith("track"):
                getapp().add_widget(
                    TrackWidget.from_file(p + ("" if p.startswith("/") else "/") + t)
                )

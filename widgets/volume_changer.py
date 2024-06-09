import pygame as pg
from app import onkey, widget, getapp
from widgets.cursor import CursorWidget
from widgets.track import TrackWidget


@widget
class VolumeChangerWidget:
    @onkey(
        pg.K_UP,
        mods=pg.KMOD_ALT,
        predicate=lambda _: not getapp().find_widget(CursorWidget).moving(),
    )
    def _(self):
        for t in getapp().find_widgets(TrackWidget):
            if t.is_selected():
                t.volume_db += 5

    @onkey(
        pg.K_DOWN,
        mods=pg.KMOD_ALT,
        predicate=lambda _: not getapp().find_widget(CursorWidget).moving(),
    )
    def _(self):
        for t in getapp().find_widgets(TrackWidget):
            if t.is_selected():
                t.volume_db -= 5

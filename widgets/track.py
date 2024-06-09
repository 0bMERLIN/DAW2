from dataclasses import dataclass
import json
from math import sin
import math
import time
from typing import Dict
from app import on, onheld, onkey, widget, getapp
from constants import TRACK_HEIGHT
from widgets.audio import AudioWidget
from widgets.drum import DrumWidget
from widgets.segment import SegmentWidget
from widgets.zoom import ZoomWidget

import pygame as pg


def collide(a: SegmentWidget, b: SegmentWidget):
    return (
        (a.start + a.length() > b.start and a.start + a.length() < b.start + b.length())
        or (a.start < b.start + b.length() and a.start > b.start)
        or (a.start == b.start and a.length() == b.length())
    )


@widget
class TrackWidget:
    track: int
    volume_db: int
    offsets: Dict[int, list]
    "...nt, Tuple[SegmentWidget, int]]"

    def from_file(path) -> "TrackWidget":
        with open(path) as f:
            data = json.load(f)
            for start, p in data["segments"]:
                if p.endswith(".wav"):
                    getapp().add_widget(AudioWidget.from_file(start, p, data["track"]))
                if p.endswith(".json"):
                    getapp().add_widget(DrumWidget.from_file(start, p, data["track"]))

            return TrackWidget(data["track"], data["volume_db"])

    def save(self, path: str):
        p = (
            path
            + ("" if path.endswith("/") else "/")
            + str("track" + str(self.track) + ".json")
        )

        segments = [
            (x.start, x.save(path))
            for x in getapp().find_widgets(SegmentWidget)
            if x.track == self.track
        ]

        with open(p, "w+") as f:
            f.write(
                json.encoder.JSONEncoder().encode(
                    {
                        "track": self.track,
                        "volume_db": self.volume_db,
                        "segments": segments,
                    }
                )
            )

    def is_selected(self):
        cursor = getapp().find_widget(CursorWidget)
        return cursor.track_cursor == self.track

    def __init__(self, track, volume_db=0):
        self.track = track
        self.offsets = {}
        self.time_last_arrangement = 0
        self.volume_db = volume_db

    def arrange_segments(self, audios):
        "arrange a set of audio widgets, such that they don't overlap"
        audios.sort(key=lambda a: (a.start, -a.length()))

        self.offsets = {id(w): [w, 0, w.start] for w in audios if w.track == self.track}

        for _ in range(len(self.offsets)):
            for w in self.offsets:
                for other in self.offsets:
                    if other == w:
                        continue
                    if self.offsets[w][1] == self.offsets[other][1] and collide(
                        self.offsets[w][0], self.offsets[other][0]
                    ):
                        self.offsets[w][1] += 1

        self.time_last_arrangement = time.time()

    def dirty(self, audios):
        "Check if audios is any different from the last arrangement"
        ids = set([*map(id, audios)])
        old_ids = set(self.offsets.keys())
        starts = sorted([x.start for x in audios])
        old_starts = sorted([x for _, _, x in self.offsets.values()])
        return ids != old_ids or starts != old_starts

    def tick(self):

        audios = [
            a for a in getapp().find_widgets(SegmentWidget) if a.track == self.track
        ]
        if audios != []:
            if time.time() - self.time_last_arrangement > 0.1 and self.dirty(audios):
                self.arrange_segments(audios)

            highest_offset = max([o for _, o, _ in self.offsets.values()]) + 1

            for w, o, _ in self.offsets.values():
                w.start = max(w.start, 0)
                self.render_audio_widget(
                    w,
                    TRACK_HEIGHT / highest_offset,
                    o,
                )
        self.draw_bg()

    def draw_bg(self):
        screen: pg.Surface = getapp().screen
        cursor = getapp().find_widget(CursorWidget)
        y = self.track * TRACK_HEIGHT

        pg.draw.line(
            screen,
            (0, 0, 0),
            (5, y),
            (5, y + TRACK_HEIGHT),
            10,
        )
        pg.draw.line(
            screen,
            (0, 255, 0),
            (5, y + TRACK_HEIGHT / 2),
            (5, y + TRACK_HEIGHT / 2 - self.volume_db * (TRACK_HEIGHT / 100)),
            10,
        )

        pg.draw.line(screen, (100, 100, 100), (0, y), (screen.get_width(), y))
        pg.draw.line(
            screen,
            (100, 100, 100),
            (0, y + TRACK_HEIGHT),
            (screen.get_width(), y + TRACK_HEIGHT),
        )

        if cursor.is_selected(self.track):
            pg.draw.rect(
                screen,
                (255, 0, 0),
                (-1, y+1, screen.get_width()+1, TRACK_HEIGHT+1),
                width=1,
            )

    def render_audio_widget(self, w: SegmentWidget, track_height, offset):
        app = getapp()

        zoom = app.find_widget(ZoomWidget).zoom
        cursor = app.find_widget(CursorWidget).cursor

        dims = w.length() * zoom, track_height

        position = (
            (w.start - cursor) * zoom + app.screen.get_width() / 2,
            TRACK_HEIGHT * w.track + track_height * offset,
        )

        pg.draw.rect(app.screen, (100, 0, 0), (*position, *dims))
        app.screen.blit(pg.transform.scale(w.visualization, dims), position)
        if w.selected:
            pg.draw.rect(
                app.screen,
                (0, 0, int(150 + (255 - 150) * (sin(time.time() * 10) + 1) / 2)),
                (*position, *dims),
                width=2,
            )
            w.selected = False


from widgets.cursor import CursorWidget

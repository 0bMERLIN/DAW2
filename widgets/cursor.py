from copy import copy
from dataclasses import dataclass, field
from math import sin
import time
from typing import List, Set
from app import onheld, onkey, onkeyup, widget, getapp
import pygame as pg

from constants import TRACK_HEIGHT
from widgets.segment import SegmentWidget
from widgets.undo import done_operation, operation
from widgets.zoom import ZoomWidget


def lines_overlap(start1, end1, start2, end2):
    if start1 > end1:
        start1, end1 = end1, start1
    if start2 > end2:
        start2, end2 = end2, start2
    return max(start1, start2) <= min(end1, end2)


@dataclass
@widget
class CursorWidget:
    # right to left selection
    cursor: int = 0
    wind_speed: int = 100  # the speed for winding backwards/forwards
    selection_start: int = 0

    clipboard: List[SegmentWidget] = None

    # track selection
    track_cursor: int = 0
    track_selection_start: int = 0
    moved_tracks = {}

    def is_selected(self, track_nr):
        a, b = sorted([self.track_selection_start, self.track_cursor])
        return track_nr in range(a, b + 1)

    @onkeyup(pg.K_LCTRL)
    def _(self):
        if len(self.moved_tracks) != 0:
            moved_tracks = copy(self.moved_tracks)

            def redo():
                for t, amt in moved_tracks.values():
                    t.start += amt

            def undo():
                for t, amt in moved_tracks.values():
                    t.start -= amt

            done_operation(redo, undo)
        self.moved_tracks = {}

    def tick(self, dt):
        # draw
        screen: pg.Surface = getapp().screen
        zoom = getapp().find_widget(ZoomWidget).zoom

        x = screen.get_width() / 2
        pg.draw.line(screen, (255, 0, 0), (x, 0), (x, screen.get_height()))
        selection_surf = pg.Surface(
            (
                abs(self.cursor - self.selection_start) * zoom,
                TRACK_HEIGHT
                * (1 + abs(self.track_cursor - self.track_selection_start)),
            )
        )
        selection_surf.set_alpha(30)
        selection_surf.fill((255,) * 3)
        screen.blit(
            selection_surf,
            (
                x - max(0, self.cursor - self.selection_start) * zoom,
                min(self.track_cursor, self.track_selection_start) * TRACK_HEIGHT,
            ),
        )

        getapp().text(10, getapp().screen.get_height() - 40, f"cursor: {self.cursor}ms")

        # logic
        if self.moving():
            self.cursor += dt
            self.selection_start = self.cursor

    def moving(self) -> bool:
        p = getapp().find_widget(PlayWidget)
        return p.is_playing() or p.is_recording()

    @onkey(pg.K_SPACE, pg.KMOD_CTRL)
    def _(self):
        if self.moving():
            return
        for d in getapp().find_widgets(DrumWidget):
            if (
                d.start <= self.cursor
                and self.cursor <= d.start + d.length()
                and self.is_selected(d.track)
            ):
                getapp().add_widget(DrumEditorWidget(d))
                return

    def shift_reset_selection(self):
        if not pg.key.get_pressed()[pg.K_LSHIFT]:
            self.track_selection_start = self.track_cursor
            self.selection_start = self.cursor
            return False
        return True

    def selected_segments(self):
        a, b = sorted([self.track_selection_start, self.track_cursor])
        return [
            s
            for s in getapp().find_widgets(SegmentWidget)
            if lines_overlap(
                self.selection_start,
                self.cursor,
                s.start,
                s.start + s.length(),
            )
            and s.track in range(a, b + 1)
        ]

    def ctrl_move_tracks(self, delta_cursor):
        if pg.key.get_pressed()[pg.K_LCTRL]:

            segments = sorted(
                self.selected_segments(),
                key=lambda s: s.start,
            )
            d = (
                0
                if self.selection_start - delta_cursor < 0
                or (len(segments) != 0 and segments[0].start + delta_cursor) < 0
                else delta_cursor
            )

            for s in segments:

                s.start += d
                s.selected = True
                if id(s) in self.moved_tracks:
                    self.moved_tracks[id(s)][1] += d
                else:
                    self.moved_tracks[id(s)] = [s, d]

            self.selection_start += d
            if d == 0:
                self.cursor -= delta_cursor

            return True
        return False

    @onkey(pg.K_DOWN)
    def _(self):
        self.track_cursor += 1
        n_tracks = len(getapp().find_widgets(TrackWidget))
        self.track_cursor = min(self.track_cursor, n_tracks - 1)
        self.shift_reset_selection()

    @onkey(pg.K_UP)
    def _(self):
        self.track_cursor -= 1
        self.track_cursor = max(0, self.track_cursor)
        self.shift_reset_selection()

    def move(self, amt):
        if self.moving():
            return
        if amt < 0:
            old_cursor = self.cursor
            self.cursor += amt
            self.cursor = max(0, self.cursor)
            self.ctrl_move_tracks(
                self.cursor - old_cursor
            ) or self.shift_reset_selection()
        else:
            self.cursor += amt
            self.ctrl_move_tracks(amt) or self.shift_reset_selection()

    @onheld(pg.K_RIGHT)
    def _(self):
        self.move(self.wind_speed)

    @onheld(pg.K_LEFT)
    def _(self):
        self.move(-self.wind_speed)

    @onkey(pg.K_c)
    def _(self):
        if self.moving():
            return
        self.clipboard = [s.copy() for s in self.selected_segments()]

    @onkey(pg.K_v)
    def _(self):
        if self.moving():
            return
        if self.clipboard == None or len(self.clipboard) == 0:
            return
        clipboard = [s.copy() for s in self.clipboard]
        first_seg = min(clipboard, key=lambda s: s.start).start
        first_track = min(clipboard, key=lambda s: s.track).track
        cursor = self.cursor
        track_cursor = self.track_cursor

        for s in clipboard:
            offset = s.start - first_seg
            s.start = max(0, cursor + offset)

            n_tracks = len(getapp().find_widgets(TrackWidget))
            track_offset = s.track - first_track
            s.track = max(0, min(n_tracks - 1, track_offset + track_cursor))

        def redo():
            getapp().add_widget(s)

        def undo():
            for seg in clipboard:
                getapp().remove_widget(seg)

        operation(redo, undo)

    @onkey(pg.K_BACKSPACE)
    def _(self):
        if self.moving():
            return
        deleted_segs = [s for s in self.selected_segments()]

        def redo():
            for s in deleted_segs:
                getapp().remove_widget(s)

        def undo():
            for i, s in enumerate(deleted_segs):
                new_s = s.copy()
                deleted_segs[i] = new_s
                getapp().add_widget(new_s)

        operation(redo, undo)

    @onkey(pg.K_BACKSPACE, pg.KMOD_CTRL)
    def _(self):
        # cut
        pass


from widgets.drum import DrumEditorWidget, DrumWidget
from widgets.play import PlayWidget
from widgets.track import TrackWidget

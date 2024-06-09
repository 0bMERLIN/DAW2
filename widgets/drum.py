from copy import copy, deepcopy
from dataclasses import dataclass
import json
import os
from typing import List

import librosa
import pydub.playback
from app import onkey, widget, getapp
from widgets.segment import SegmentWidget
from pydub import AudioSegment
import pygame as pg
import pydub

import widgets.undo as undo


def load_kit(kit_path):
    def helper(p):
        return AudioSegment.from_file(kit_path + p)

    return [*map(helper, os.listdir(kit_path))]


@dataclass
@widget
class DrumWidget(SegmentWidget):
    start: int
    pattern: List[List[bool]]
    track: int
    subdivision: int
    bpm: int
    kit_path: str
    kit: List[AudioSegment]
    visualization: pg.Surface

    def copy(self) -> "DrumWidget":
        d = DrumWidget(
            self.start,
            deepcopy(self.pattern),
            self.track,
            self.subdivision,
            self.bpm,
            deepcopy(self.kit_path),
            copy(self.kit),
            None,
        )
        d.visualize()
        return d

    def save(self, path: str):
        p = path + ("" if path.endswith("/") else "/") + str(id(self)) + ".json"
        with open(p, "w+") as f:
            f.write(
                json.encoder.JSONEncoder().encode(
                    {
                        "pattern": self.pattern,
                        "bpm": self.bpm,
                        "subdivision": self.subdivision,
                    }
                )
            )
            return p

    def length(self):
        return (60_000 / self.bpm) * (
            max([len(x) for x in self.pattern]) / (self.subdivision / 4)
        )

    def to_audio_segment(self) -> AudioSegment:

        res = AudioSegment.silent(self.length() + len(self.kit[0]))

        for sound, drum in zip(self.kit, self.pattern):
            for n, hit in enumerate(drum):
                if not hit:
                    continue
                res = res.overlay(
                    sound, (n / (self.subdivision / 4)) * (60_000 / self.bpm)
                )
        return res

    def visualize(self):
        self.visualization = pg.Surface((500, 100))
        self.visualization.fill((0, 0, 100))
        for y, drum in enumerate(self.pattern):
            for x, hit in enumerate(drum):
                if not hit:
                    continue
                cell_w = self.visualization.get_width() / max(
                    [len(x) for x in self.pattern]
                )
                cell_h = self.visualization.get_height() / len(self.kit)
                pg.draw.rect(
                    self.visualization,
                    (0, 0, 255),
                    (x * cell_w, y * cell_h, cell_w, cell_h),
                )

    def from_file(start: int, path: str, track: int):
        with open(path, "r") as p:

            data = json.load(p)
            d = DrumWidget(
                start,
                data["pattern"],
                track,
                data["subdivision"],
                data["bpm"],
                "drums/1/",
                load_kit("drums/1/"),
                None,
            )
            d.visualize()
            return d

    def basic(start: int, track: int, bpm=180):
        "make a basic, 4 beat track"
        kit = load_kit("drums/1/")
        d = DrumWidget(
            start,
            [([False] * 4) for _ in kit],
            track,
            4,
            bpm,
            "drums/1/",
            kit,
            None,
        )
        d.visualize()
        return d


def play_with_simpleaudio(path):
    y, sr = librosa.load(path)
    wav_bytes = y.tobytes()

    s = AudioSegment(
        wav_bytes,
        frame_rate=sr,
        sample_width=y.dtype.itemsize,
        channels=1,  # Assuming mono audio
    )
    pydub.playback._play_with_simpleaudio(s)


@dataclass
@widget
class DrumEditorWidget:
    editing: DrumWidget
    x: int = 0
    y: int = 0

    def tick(self):
        screen: pg.Surface = getapp().screen
        W, H = screen.get_width() - 20, screen.get_height() - 20
        pg.draw.rect(screen, (10, 97, 100), (10, 10, W, H))

        cell_w = W / max([len(x) for x in self.editing.pattern])
        cell_h = H / len(self.editing.kit)
        for y, drum in enumerate(self.editing.pattern):
            for x, hit in enumerate(drum):
                if not hit:
                    continue
                pg.draw.rect(
                    screen,
                    (0, 0, 255),
                    (10 + x * cell_w, 10 + y * cell_h, cell_w, cell_h),
                )

        pg.draw.rect(
            screen,
            (255, 0, 0),
            (10 + self.x * cell_w, 10 + self.y * cell_h, cell_w, cell_h),
            5,
        )

        pg.draw.rect(screen, (10, 47, 50), (5, 5, W + 5, H + 5), width=5)
        pg.draw.rect(screen, (10, 30, 50), (5, H - 10, W + 5, 50))

        getapp().centered_text(
            W / 2,
            H - 10,
            f"========== BPM: {self.editing.bpm}, SUBDIVISION: {self.editing.subdivision} ==========",
        )

    @onkey(pg.K_r, pg.KMOD_CTRL)
    def lengthen(self):
        def do():
            for i in range(len(self.editing.pattern)):
                self.editing.pattern[i] += [False]
            self.editing.visualize()

        undo.operation(do, lambda: (self.shorten(), self.editing.visualize()))

    @onkey(pg.K_BACKSPACE)
    def shorten(self):
        elems = []

        def do(elems: list):
            if len(self.editing.pattern) <= 1:
                return
            elems.clear()
            elems += [
                self.editing.pattern[i].pop() for i in range(len(self.editing.pattern))
            ]
            self.editing.visualize()

        undo.operation(
            lambda: do(elems),
            lambda: (
                [self.editing.pattern[i].append(e) for i, e in enumerate(elems)],
                self.editing.visualize(),
            ),
        )

    @onkey(pg.K_SPACE, pg.KMOD_CTRL)
    def _(self):
        getapp().remove_widget(self)

    @onkey(pg.K_SPACE)
    def _(self):
        self.editing.pattern[self.y][self.x] = not self.editing.pattern[self.y][self.x]
        if self.editing.pattern[self.y][self.x]:
            play_with_simpleaudio(
                self.editing.kit_path + os.listdir(self.editing.kit_path)[self.y]
            )
        self.editing.visualize()

    @onkey(pg.K_LEFT)
    def _(self):
        self.x = (self.x - 1) % len(self.editing.pattern[0])

    @onkey(pg.K_RIGHT)
    def _(self):
        self.x = (self.x + 1) % len(self.editing.pattern[0])

    @onkey(pg.K_UP)
    def _(self):
        self.y = (self.y - 1) % len(self.editing.pattern)

    @onkey(pg.K_DOWN)
    def _(self):
        self.y = (self.y + 1) % len(self.editing.pattern)

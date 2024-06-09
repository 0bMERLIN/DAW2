from dataclasses import dataclass
import os
import signal
import subprocess
from tempfile import NamedTemporaryFile
import threading
import time
from typing import Tuple

from app import widget, getapp, onkey
import pygame as pg

from pydub import AudioSegment

from widgets.drum import DrumWidget
from widgets.segment import SegmentWidget
from widgets.track import TrackWidget


def get_pid(name):
    return [*map(int, subprocess.check_output(["pidof", name]).split())]


def play(seg):
    def test():
        PLAYER = "ffplay"
        with NamedTemporaryFile("w+b", suffix=".mp3") as f:
            seg.export(f.name, "mp3")
            subprocess.call(
                [PLAYER, "-nodisp", "-autoexit", "-hide_banner", f.name],
            )

    thread = threading.Thread(target=test)
    thread.start()
    return thread


def stop():
    try:
        for pid in get_pid("ffplay"):
            os.system(f"kill -9 {pid}")
    except:
        pass


def play_icon(x, y, h):
    pg.draw.polygon(
        getapp().screen, (0, 230, 0), [(x, y), (x + h, y + h / 2), (x, y + h)]
    )


def pause_icon(x, y, w):
    pg.draw.rect(getapp().screen, (0, 230, 0), (x, y, w / 3, w))
    pg.draw.rect(getapp().screen, (0, 230, 0), (x + w / 1.5, y, w / 3, w))


def record_icon(x, y, w):
    pg.draw.circle(getapp().screen, (255, 0, 0), (x + w / 2, y + w / 2), w / 2)


@widget
@dataclass
class PlayWidget:
    "Handles starting playback/recording"

    monitor = False

    _playback: threading.Thread = None
    _recording: Tuple[subprocess.Popen, "AudioWidget"] | None = None

    def is_recording(self) -> bool:
        return self._recording != None

    def is_playing(self) -> bool:
        return pg.mixer.music.get_busy()

    def draw(self):
        w = getapp().screen.get_width()
        if self.is_playing():
            play_icon(w - 60, 10, 50)
        else:
            pause_icon(w - 60, 10, 50)
        if self.is_recording():
            record_icon(w - 120, 10, 50)

    def tick(self, dt):
        self.draw()

        if self.is_recording():
            x = AudioSegment.silent(dt)
            self._recording[1].audio_data += x
            render_audio(
                self._recording[1].audio_data, self._recording[1].visualization
            )

    # render the audio into a single segment
    def render(self) -> AudioSegment:
        audios = getapp().find_widgets(SegmentWidget)
        if audios == []:
            return None
        length = max([a.length() + a.start for a in audios])
        gains = {t.track: t.volume_db for t in getapp().find_widgets(TrackWidget)}
        c = AudioSegment.silent(length)
        for a in audios:
            match a:
                case AudioWidget():
                    c = c.overlay(a.audio_data.apply_gain(gains[a.track]), a.start)

                case DrumWidget():
                    c = c.overlay(
                        a.to_audio_segment().apply_gain(gains[a.track]), a.start
                    )

        return c

    def start_playing(self):
        cursor = getapp().find_widget(CursorWidget).cursor
        track = self.render()
        if track == None:
            return
        if cursor < len(track):
            start_time = time.time() * 1000
            track.export("song.mp3")
            pg.mixer.music.load("song.mp3")
            os.remove("song.mp3")
            pg.mixer.music.play()
            pg.mixer.music.set_pos(cursor / 1000)
            delay = int(100 + time.time() * 1000 - start_time)
            getapp().find_widget(CursorWidget).cursor -= delay

    def stop_playing(self):
        pg.mixer.music.stop()
        self._playback = None

    @onkey(pg.K_r, pg.KMOD_CTRL)
    def _(self):
        "add a drum track"
        dw = DrumWidget.basic(
            getapp().find_widget(CursorWidget).cursor,
            getapp().find_widget(CursorWidget).track_cursor,
            bpm=([d.bpm for d in getapp().find_widgets(DrumWidget)] + [180])[0],
        )
        undo.operation(
            lambda: getapp().add_widget(dw), lambda: getapp().remove_widget(dw)
        )

    @onkey(pg.K_SPACE)
    def _(self):
        if self.is_recording():
            self.stop_recording()
        elif self.is_playing():
            self.stop_playing()
        else:
            self.start_playing()

    def cleanup(self):
        print("CRASH: cleaning up PlayWidget....")
        if self._recording != None:
            os.killpg(self._recording[0].pid, signal.SIGTERM)
            self._recording[0].terminate()
            try:
                os.remove("last_recording.wav")
            except:
                pass
            if self.monitor:
                os.system("pactl unload-module module-loopback")

    def stop_recording(self):
        if self.is_playing():
            self.stop_playing()

        if self.monitor:
            os.system("pactl unload-module module-loopback")
        os.killpg(self._recording[0].pid, signal.SIGTERM)
        self._recording[0].terminate()

        # TODO: speed this up.
        w = AudioWidget.from_file(
            self._recording[1].start - LATENCY,
            "last_recording.wav",
            self._recording[1].track,
        )
        undo.operation(
            lambda: getapp().add_widget(w), lambda: getapp().remove_widget(w)
        )

        getapp().remove_widget(self._recording[1])
        self._recording = None
        os.remove("last_recording.wav")

    def start_recording(self):
        self.stop_playing()
        self.start_playing()

        if self.monitor:
            os.system("pactl load-module module-loopback latency_msec=4")

        recording_process = subprocess.Popen(
            ["arecord", "-vv", "--format=cd", "last_recording.wav"],
            shell=False,
            preexec_fn=os.setsid,
        )
        self._recording = (
            recording_process,
            None,
        )  # for safety, if anything after this crashes...

        recording_widget = AudioWidget.dummy(
            getapp().find_widget(CursorWidget).cursor,
            (0, 0),
            getapp().find_widget(CursorWidget).track_cursor,
        )
        getapp().add_widget(recording_widget)
        self._recording = (recording_process, recording_widget)

    @onkey(pg.K_r)
    def _(self):
        if not self.is_recording():
            self.start_recording()
        else:
            self.stop_recording()


from constants import LATENCY
from widgets.audio import AudioWidget, render_audio
from widgets.cursor import CursorWidget
import widgets.undo as undo

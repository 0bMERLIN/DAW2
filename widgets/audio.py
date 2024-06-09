from dataclasses import dataclass
from typing import Callable, Tuple
import librosa
from app import getapp, widget
import pygame as pg
from pydub import AudioSegment
from pydub.generators import Sine

from constants import TRACK_HEIGHT
from widgets.segment import SegmentWidget
from widgets.zoom import ZoomWidget


def render_audio(audio_segment: AudioSegment, surface: pg.Surface):
    data = audio_segment.get_array_of_samples()
    if len(data) < 100:
        return

    BARS = int(len(data) / 100)
    BAR_HEIGHT = 100
    LINE_WIDTH = surface.get_width() / BARS

    length = len(data)
    RATIO = length / BARS

    count = 0
    maximum_item = 0
    max_array = []
    highest_line = 0

    for d in data:
        if count < RATIO:
            count = count + 1

            if abs(d) > maximum_item:
                maximum_item = abs(d)
        else:
            max_array.append(maximum_item)

            if maximum_item > highest_line:
                highest_line = maximum_item

            maximum_item = 0
            count = 1

    current_x = 1
    line_ratio = highest_line / BAR_HEIGHT
    for item in max_array:
        item_height = 1 if line_ratio == 0 else item / line_ratio

        current_y = (BAR_HEIGHT - item_height) / 2
        pg.draw.line(
            surface,
            (255, 0, 0),
            (current_x, current_y),
            (current_x, current_y + item_height),
        )

        current_x = current_x + LINE_WIDTH


def load_audio(path):
    y, sr = librosa.load(path)
    wav_bytes = y.tobytes()
    return AudioSegment(
        wav_bytes,
        frame_rate=sr,
        sample_width=y.dtype.itemsize,
        channels=1,  # Assuming mono audio
    )


@dataclass
@widget
class AudioWidget(SegmentWidget):
    # playable audio != renderable audio
    # (probably due to a bug regarding pydub)
    start: int
    audio_data: AudioSegment

    visualization: pg.Surface
    track: int
    "The track the audio segment belongs to"

    def copy(self) -> "AudioWidget":
        d = AudioWidget(
            self.start,
            self.audio_data[:len(self.audio_data)],
            pg.Surface((500, 100)),
            self.track,
        )
        render_audio(d.audio_data, d.visualization)

        return d

    def save(self, path: str):
        p = path + ("" if path.endswith("/") else "/") + str(id(self)) + ".wav"
        self.audio_data.export(p, "wav")
        return p

    def length(self) -> int:
        return len(self.audio_data)

    def map(self, fn: Callable[[AudioSegment], None]):  # fn must be pure
        fn(self.audio_data)
        render_audio(self.audio_data, self.visualization)
        self.visualization = pg.transform.scale(self.visualization, self.size)

    def from_file(start: int, path: str, track):
        data = AudioSegment.from_file(path)
        if start < 0:
            start = 0
            data = data[-start:]
        d = AudioWidget(
            start,
            data,
            pg.Surface((500, 100)),
            track,
        )
        render_audio(d.audio_data, d.visualization)

        return d

    def from_sine(start: int, length: int, freq: int, offset: Tuple[int, int], track):
        sine_generator = Sine(300)
        d = AudioWidget(
            start,
            sine_generator.to_audio_segment(duration=length),
            sine_generator.to_audio_segment(duration=length),
            pg.Surface((500, 100)),
            offset,
            track,
        )
        render_audio(d.audio_data, d.visualization)

        return d

    def dummy(start: int, offset: Tuple[int, int], track):
        d = AudioWidget(
            start,
            AudioSegment.silent(1),
            pg.Surface((500, 100)),
            track,
        )
        render_audio(d.audio_data, d.visualization)

        return d


from widgets.cursor import CursorWidget

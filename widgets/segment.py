import pygame as pg


class SegmentWidget:
    "A segment in the song."
    start: int
    track: int
    visualization: pg.Surface
    selected: bool = False

    def copy(self) -> "SegmentWidget":
        pass

    def length(self) -> int:
        pass

    def save(self, path: str) -> str:
        "take in a project folder path and return the name of the file saved to"
        pass

    def from_file(start: int, path: str, track: int) -> "SegmentWidget":
        pass

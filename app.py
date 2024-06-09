from dataclasses import dataclass
import time
from typing import Callable, Dict, List, TypeVar
import pygame as pg


@dataclass
class Event:
    data: pg.event.Event
    processed: bool = False


class App:
    widgets: List["Widget"]
    events: List[Event]
    screen: pg.Surface
    clock: pg.time.Clock
    new_widgets: List["Widget"]
    removed_widgets: List[int]
    handled_pressed: list  # pg.K_...
    keys_down: list  # pg.K_...
    _instance: "App" = None

    import pygame as pg

    def text(self, x, y, s):
        self.screen.blit(self.MONOSPACE.render(str(s), True, (255, 255, 255)), (x, y))

    def centered_text(self, x, y, s):
        img = self.MONOSPACE.render(str(s), True, (255, 255, 255))
        self.screen.blit(img, (x - img.get_width() / 2, y))

    T = TypeVar("T")

    def find_widgets(_, cls: type[T]) -> List[T]:
        return [w for w in App.get_instance().widgets if isinstance(w, cls)]

    def find_widget(_, cls: type[T]) -> T:
        """
        Try to find a widget of the given type
        Raises `RuntimeError` otherwise
        """
        ws = getapp().find_widgets(cls)
        if len(ws) == 0:
            raise RuntimeError(f"Widget of type {cls} not found!")
        else:
            return ws[0]

    def get_instance() -> "App":
        if App._instance == None:
            App._instance = App()

        return App._instance

    def init(screen_size=(800, 480)):
        self = App.get_instance()
        pg.init()
        self.screen = pg.display.set_mode(screen_size)
        self.widgets = []
        self.events = []
        self.new_widgets = []
        self.removed_widgets = []
        self.handled_pressed = []
        self.keys_down = []

        pg.mixer.init()

        pg.font.init()
        self.MONOSPACE = pg.font.SysFont("monospace", 24)

    def add_widget(self, w):
        self.new_widgets += [w]

    def remove_widget(self, w: "Widget"):
        self.removed_widgets += [id(w)]

    def start(self):
        try:
            self.clock = pg.time.Clock()
            while True:
                dt = self.clock.tick(60)
                self.tick(dt)
        finally:
            for w in self.widgets:
                if hasattr(w, "cleanup"):
                    w.cleanup()

    def tick(self, dt):
        self.screen.fill((47, 79, 79))

        # get pg events
        self.events = [Event(e) for e in pg.event.get()]

        for e in self.events:
            if e.data.type == pg.KEYUP and e.data.key in self.keys_down:
                self.keys_down.remove(e.data.key)

        self.handled_pressed = []

        self.widgets = list(self.new_widgets)
        self.new_widgets = []

        for w in self.widgets:
            if id(w) in self.removed_widgets:
                continue

            # do a tick
            if hasattr(w, "tick"):
                if argcount(w.tick) == 2:
                    w.tick(dt)
                else:
                    w.tick()
            self.new_widgets += [w]

        self.removed_widgets = []

        for w in reversed(self.widgets):
            if id(w) in self.removed_widgets:
                continue

            listeners = [
                getattr(w, func)
                for func in dir(w)
                if callable(getattr(w, func)) and func.startswith("_on_")
            ]
            for l in listeners:
                l()
        

        pg.display.flip()


getapp = App.get_instance


class Widget:

    def tick(self):
        pass


# class decorator
WIDGET_LISTENERS: Dict[str, Dict[str, Callable]] = {}


def widget(cls):

    # add listeners
    if cls.__name__ in WIDGET_LISTENERS:
        for nm, f in WIDGET_LISTENERS[cls.__name__].items():
            setattr(cls, nm, f)
            f.__name__ = nm

    return cls


def argcount(func: Callable) -> int:
    return func.__code__.co_argcount


def register_listener(f, class_name, name):
    global WIDGET_LISTENERS
    if class_name not in WIDGET_LISTENERS:
        WIDGET_LISTENERS[class_name] = {}
    WIDGET_LISTENERS[class_name][name] = f
    return f


def on(predicate: Callable[[pg.event.Event, Widget], bool], event_name: str):
    def decorate(func):
        argc = argcount(func)
        if argc not in [1, 2]:
            raise TypeError(
                f"{func} takes {argcount(func)} arguments, but should take 1 or 2."
            )

        def new_func(self: Widget):
            for e in getapp().events:

                if (
                    predicate(e, self)
                    and not e.processed
                    and not (
                        e.data.type == pg.KEYDOWN
                        and e.data.key in getapp().handled_pressed
                    )
                ):
                    e.processed = True
                    if e.data.type == pg.KEYDOWN:
                        getapp().keys_down += [e.data.key]

                    if argc == 2:
                        func(self, e.data)
                    elif argc == 1:
                        func(self)
                    break

        register_listener(
            new_func, func.__qualname__.split(".")[0], f"_on_{event_name}"
        )
        return new_func

    return decorate


def onheld(key, predicate: Callable[[Widget], bool] = lambda _: True):
    def decorate(func):
        def new_func(self: Widget):
            if (
                key not in getapp().handled_pressed
                and key not in getapp().keys_down
                and pg.key.get_pressed()[key]
                and predicate(self)
            ):
                getapp().handled_pressed += [key]
                func(self)

        register_listener(
            new_func, func.__qualname__.split(".")[0], f"_on_{key}_{id(predicate)}"
        )
        return new_func

    return decorate


def onkey(key, mods=None, predicate: Callable[[Widget], bool] = lambda _: True):
    return on(
        lambda e, self: isinstance(e.data, pg.event.Event)
        and e.data.type == pg.KEYDOWN
        and e.data.key == key
        and (mods == None or e.data.mod & mods)
        and predicate(self),
        f"_on_{key}_{mods}_{id(predicate)}",
    )

def onkeyup(key, mods=None):
    return on(
        lambda e, _: isinstance(e.data, pg.event.Event)
        and e.data.type == pg.KEYUP
        and e.data.key == key
        and (mods == None or e.data.mod & mods),
        str(key) + str(mods),
    )


def onevent(event_type):
    return on(
        lambda e, _: isinstance(e.data, pg.event.Event) and e.data.type == event_type,
        str(event_type),
    )

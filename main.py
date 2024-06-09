import app
from widgets.cursor import CursorWidget
from widgets.play import PlayWidget
from widgets.save import SaveWidget
from widgets.undo import UndoWidget
from widgets.volume_changer import VolumeChangerWidget
from widgets.zoom import ZoomWidget

app.App.init()

myapp = app.App.get_instance()

myapp.add_widget(ZoomWidget())
s = SaveWidget()
myapp.add_widget(s)
s.load()
myapp.add_widget(CursorWidget())
myapp.add_widget(VolumeChangerWidget())
myapp.add_widget(PlayWidget())
myapp.add_widget(UndoWidget())

myapp.start()

"""

TODO

drums:
    - change bpm
range selection:
    - cut or split individual segments


project manager:
    - separate screen, list recent projects
    - go into project
    - add / delete projects

"""

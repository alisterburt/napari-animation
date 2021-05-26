from pathlib import Path

from napari import Viewer
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QErrorMessage,
    QFileDialog,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..animation import Animation
from .frame_widget import FrameWidget
from .keyframelistcontrol_widget import KeyFrameListControlWidget
from .keyframeslist_widget import KeyFramesListWidget


class AnimationWidget(QWidget):
    """Widget for interatviely making animations using the napari viewer.

    Parameters
    ----------
    viewer : napari.Viewer
        napari viewer.

    Attributes
    ----------
    viewer : napari.Viewer
        napari viewer.
    animation : napari_animation.Animation
        napari-animation animation in sync with the GUI.
    """

    def __init__(self, viewer: Viewer, parent=None):
        super().__init__(parent=parent)

        # Store reference to viewer and create animation
        self.viewer = viewer
        self.animation = Animation(self.viewer)

        # Initialise User Interface
        self.keyframesListControlWidget = KeyFrameListControlWidget(
            animation=self.animation, parent=self
        )
        self.keyframesListWidget = KeyFramesListWidget(
            self.animation.key_frames, parent=self
        )
        self.frameWidget = FrameWidget(parent=self)
        self.saveButton = QPushButton("Save Animation", parent=self)
        self.animationSlider = QSlider(Qt.Horizontal, parent=self)
        self.animationSlider.setToolTip("Scroll through animation")
        self.animation._frames.events.n_frames.connect(
            lambda e: self.animationSlider.setMaximum(e.value)
        )

        self.animationSlider.setMaximum(len(self.animation._frames) - 1)

        # Create layout
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.keyframesListControlWidget)
        self.layout().addWidget(self.keyframesListWidget)
        self.layout().addWidget(self.frameWidget)
        self.layout().addWidget(self.saveButton)
        self.layout().addWidget(self.animationSlider)

        # establish key bindings and callbacks
        self._add_keybind_callbacks()
        self._add_callbacks()

    def _add_keybind_callbacks(self):
        """Bind keys"""
        self._keybindings = [
            ("Alt-f", self._capture_keyframe_callback),
            ("Alt-r", self._replace_keyframe_callback),
            ("Alt-d", self._delete_keyframe_callback),
            ("Alt-a", lambda e: self.animation.key_frames.select_next()),
            ("Alt-b", lambda e: self.animation.key_frames.select_previous()),
        ]
        for key, cb in self._keybindings:
            self.viewer.bind_key(key, cb)

    def _add_callbacks(self):
        """Establish callbacks"""
        self.keyframesListControlWidget.deleteButton.clicked.connect(
            self._delete_keyframe_callback
        )
        self.keyframesListControlWidget.captureButton.clicked.connect(
            self._capture_keyframe_callback
        )
        self.saveButton.clicked.connect(self._save_callback)
        self.animationSlider.valueChanged.connect(
            self._move_animationslider_callback
        )

        keyframe_list = self.animation.key_frames
        keyframe_list.events.inserted.connect(self._on_keyframes_changed)
        keyframe_list.events.removed.connect(self._on_keyframes_changed)
        keyframe_list.events.changed.connect(self._on_keyframes_changed)

    def _input_state(self):
        """Get current state of input widgets as {key->value} parameters."""
        return {
            "steps": int(self.frameWidget.stepsSpinBox.value()),
            "ease": self.frameWidget.get_easing_func(),
        }

    def _capture_keyframe_callback(self, event=None):
        """Record current key-frame"""
        self.animation.capture_keyframe(**self._input_state())

    def _replace_keyframe_callback(self, event=None):
        """Replace current key-frame with new view"""
        self.animation.capture_keyframe(**self._input_state(), insert=False)

    def _delete_keyframe_callback(self, event=None):
        """Delete current key-frame"""
        self.animation.key_frames.remove_selected()

    def _on_keyframes_changed(self, event=None):
        has_frames = bool(self.animation.key_frames)

        self.keyframesListControlWidget.deleteButton.setEnabled(has_frames)
        self.keyframesListWidget.setEnabled(has_frames)
        self.frameWidget.setEnabled(has_frames)

    def _save_callback(self, event=None):

        if len(self.animation.key_frames) < 2:
            error_dialog = QErrorMessage()
            error_dialog.showMessage(
                f"You need at least two key frames to generate \
                an animation. Your only have {len(self.animation.key_frames)}"
            )
            error_dialog.exec_()

        else:
            filters = (
                "Video files (*.mp4 *.gif *.mov *.avi *.mpg *.mpeg *.mkv *.wmv)"
                ";;Folder of PNGs (*)"  # sep filters with ";;"
            )
            filename, _filter = QFileDialog.getSaveFileName(
                self, "Save animation", str(Path.home()), filters
            )
            if filename:
                self.animation.animate(filename)

    def _move_animationslider_callback(self, new_frame: int):
        """Set the animation to the specified (interpolated) frame index."""
        self.animation.set_movie_frame_index(new_frame)

    def closeEvent(self, ev) -> None:
        # release callbacks
        for key, _ in self._keybindings:
            self.viewer.bind_key(key, None)
        return super().closeEvent(ev)

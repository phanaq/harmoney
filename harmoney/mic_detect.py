#! /usr/bin/env python

import sys
sys.path.append('..')
from common.core import *
from common.audio import *
from common.mixer import *
from common.wavegen import *
from common.wavesrc import *

from common.gfxutil import *
from aubio import source, pitch

from kivy.graphics import Color, Line
from kivy.graphics.instructions import InstructionGroup

w = Window.width
h = Window.height

class Staff(InstructionGroup) :
    def __init__(self, bottom_y, line_width):
        super(Staff, self).__init__()
        self.bottom_y = bottom_y
        self.line_width = line_width
        lines = []
        for i in range(1,6):
            line_height = i*line_width + bottom_y
            line = Line(points=[0, line_height, w, line_height])
            lines.append(line)
        for line in lines:
            self.add(line)

class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()

        self.audio = Audio(2, input_func=self.receive_audio)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)

        self.record = True
        self.input_buffers = []

        self.label = topleft_label()
        self.add_widget(self.label)
        self.label.text = "0"
        
        self.staff = Staff(100, 50)
        self.canvas.add(self.staff)

        self.pitch = 0
        self.anim_group = AnimGroup()
        self.canvas.add(self.anim_group)
        self.pointer = Pointer(self.staff)
        self.anim_group.add(self.pointer)

        self.setup()

    def setup(self):
        self.downsample = 1
        self.samplerate = 44100 // self.downsample
        if len( sys.argv ) > 2: self.samplerate = int(sys.argv[2])

        self.win_s = 4096 // self.downsample # fft size
        self.hop_s = 512  // self.downsample # hop size

        self.tolerance = 0.8

        self.pitch_o = pitch("yin", self.win_s, self.hop_s, self.samplerate)
        self.pitch_o.set_unit("midi")
        self.pitch_o.set_tolerance(self.tolerance)

    def on_update(self):
        self.audio.on_update()
        self.anim_group.on_update()

        if self.record:
            if len(self.input_buffers) > 0:
                pitch = self.pitch_o(self.input_buffers.pop(0)[:512])[0]
                pitch = int(round(pitch))
                if pitch != self.pitch:
                    self.pitch = pitch
                    self.pointer.set_pitch(self.pitch)
                self.label.text = str(pitch)

    def receive_audio(self, frames, num_channels):
        if self.record:
            self.input_buffers.append(frames)

    def on_key_down(self, keycode, modifiers):
        # start recording
        if keycode[1] == 'r':
            self.record = False if self.record else True

    def _process_input(self) :
        pass

run(MainWidget)
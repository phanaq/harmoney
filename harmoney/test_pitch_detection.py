#! /usr/bin/env python

import sys
sys.path.append('..')
from common.core import *
from common.audio import *
from common.wavegen import *
from common.wavesrc import *
from common.gfxutil import *

from aubio import source, pitch

from collections import Counter

class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()

        self.unrounded_pitch = 0
        self.pitch = 0
        self.algorithm = "yin"
        self.tolerance = 0.9

        self.audio = Audio(2, input_func=self.receive_audio)

        self.label = Label(text = "text", valign='top', font_size='15sp',
              pos=(Window.width*.5, Window.height * 0.4),
              text_size=(Window.width, Window.height))
        self.add_widget(self.label)
        
        self.setUp()

        self.pitch_window_size = 30
        self.previous_pitches = []

        self.input_buffers = []

        self.smoothed_pitch = 0

    def setUp(self):
        self.downsample = 1
        self.samplerate = 44100 // self.downsample
        if len( sys.argv ) > 2: self.samplerate = int(sys.argv[2])

        self.hop_s = 512  // self.downsample # hop size
        self.win_s = (self.hop_s * 8) // self.downsample # fft size

        self.pitch_o = pitch(self.algorithm, self.win_s, self.hop_s, self.samplerate)
        self.pitch_o.set_unit("midi")
        self.pitch_o.set_tolerance(self.tolerance)

    def on_update(self):
        self.audio.on_update()

        if len(self.input_buffers) > 0:
            pitch = self.pitch_o(self.input_buffers.pop(0)[:512])[0]
            self.unrounded_pitch = pitch
            pitch = int(round(pitch))
            if len(self.previous_pitches)>self.pitch_window_size:
                self.previous_pitches.pop(0)
            self.previous_pitches.append(pitch)
            if pitch != self.pitch:
                self.pitch = pitch

        pitch_counter = Counter(self.previous_pitches)
        counter_string = 'String counts: \n'
        for item in pitch_counter.most_common():
            counter_string += str(item)
            counter_string += '\n'

        cur_pitch = self.pitch
        most_common = pitch_counter.most_common()
        if len(most_common) > 0:
            mc_pitch = most_common[0][0]
            if cur_pitch == mc_pitch:
                self.smoothed_pitch = cur_pitch


        self.label.text = 'up/down to change tolerance \n'  
        self.label.text += 'Algorithm: ' + self.algorithm + '\n'
        self.label.text += 'Tolerance: ' + str(self.tolerance) + '\n'
        self.label.text += 'Detected: '+str(self.unrounded_pitch)+'\n'
        self.label.text += 'Rounded pitch: '+str(self.pitch) + '\n'
        self.label.text += 'Smoothed pitch: '+str(self.smoothed_pitch) + '\n'
        self.label.text += counter_string

    def receive_audio(self, frames, num_channels):
        self.input_buffers.append(frames)

    def on_key_down(self, keycode, modifiers):
        updown = lookup(keycode[1], ('up', 'down'), (.01, -.01))
        if updown:
            self.tolerance += updown
            self.pitch_o.set_tolerance(self.tolerance)

    def _process_input(self) :
        pass

run(MainWidget)
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
            

class NoteBlock(InstructionGroup):
    def __init__(self, pos, width):
        super(NoteBlock, self).__init__()
        self.height = 30
        self.width = width
        self.pos = (pos[0], pos[1] - self.height / 2)
        self.color = Color(0, 1, 0)
        self.rect = Rectangle(pos=self.pos, size=(self.width, self.height))
        self.add(self.color)
        self.add(self.rect)

    def on_hit(self):
        pass

    def on_pass(self):
        pass


# holds data for gems and barlines.
class SongData(object):
    def __init__(self):
        super(SongData, self).__init__()

        # list of tuples of the form (midi value, start time, duration)
        self.notes = []

    # read the annotation data
    # notes are annotated by their midi value, with periods of silence labelled by 0
    def read_data(self, solo_file):
        solo = open(solo_file)
        lines = solo.readlines()

        # for each line, remove \n and split by \t
        for ind in range(len(lines)):
            line = lines[ind]
            tokens = line.strip().split("\t")

            # 0 means silence
            if int(tokens[1]) != 0:

                # get start time of next note to calculate duration
                next_line = lines[ind+1]
                next_tokens = next_line.strip().split("\t")
                self.notes.append((int(tokens[1]), float(tokens[0]), float(next_tokens[0]) - float(tokens[0])))

    def get_notes(self):
        return self.notes


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

        self.testBlock = NoteBlock((100, 150), 100)
        self.testBlock2 = NoteBlock((200, 200), 100)
        self.canvas.add(self.testBlock)
        self.canvas.add(self.testBlock2)

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

        self.filename = 'treat_you_better.wav'
        self.wave_gen = WaveGenerator(WaveFile(self.filename))
        self.wave_gen.frame = 44100 * 28
        self.wave_gen.pause()
        self.mixer.add(self.wave_gen)

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

        if keycode[1] == 'p':
            print 'toggle song'
            self.wave_gen.play_toggle()

    def _process_input(self) :
        pass

run(MainWidget)
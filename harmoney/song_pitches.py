#! /usr/bin/env python

import sys
sys.path.append('..')
from common.core import *
from common.audio import *
from common.mixer import *
from common.wavegen import *
from common.wavesrc import *
from common.clock import *
from common.kivyparticle import ParticleSystem

from common.gfxutil import *
from aubio import source, pitch

from kivy.core.window import Window
# from kivy.graphics import Color, Line
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.graphics.instructions import InstructionGroup
from kivy.clock import Clock as kivyClock

from harmony_detect import *

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


#colors for note blocks: white, pink, red, orange, yellow, green, light blue, dark blue, purple
rainbowRGB = [(1, 1, 1), (1, .4, 1), (1, 0, 0), (1, .4, 0), (1, 1, 0), (.4, 1, .2), (0, 1, 1), (0, 0, 1), (.4, 0, .8)]

class NoteBlock(InstructionGroup): # modified from lab4
    def __init__(self, pitch, duration, floorY, ceilingY, color, xpos):
        super(NoteBlock, self).__init__()

        x = xpos
        y = np.interp(pitch, [58, 77], [floorY, ceilingY])

        self.color = color
        self.color.a = .65
        #length of block is directly proportional to duration

        self.rect = Rectangle(size = (float(duration) * 200, 30), pos=(x,y))

        self.add(self.color)
        self.add(self.rect)

    def on_update(self):
        pass

class TrackData(object):
    # def __init__(self, gem_file, barline_file):
    def __init__(self, solo_file):  
        super(TrackData, self).__init__()
        self.notes = []
        self.note_dict = {}
        self.read_data(solo_file)
        for note in self.notes:
            start_time = note[1]
            pitch = note[0]
            dur = note[2]
            self.note_dict[start_time] = (pitch, dur)


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
                self.notes.append((int(tokens[1])+1, float(tokens[0]), float(next_tokens[0]) - float(tokens[0])))

    def get_notes(self):
        return self.note_dict #dict w key = note times, val = (pitch, dur)

    # return a sublist of the notes that match this time slice:
    def get_notes_in_range(self, start_time, end_time):
        notes_in_range = []
        for note_time in self.note_dict:
            if note_time >= start_time and note_time <= end_time:
                notes_in_range.append((note_time, self.note_dict[note_time][0], self.note_dict[note_time][1]))
        return notes_in_range #list of gem times


class PointerDisplay(InstructionGroup):
    def __init__(self, nowbar_offset, ps):
        super(PointerDisplay, self).__init__()
        self.anim_group = AnimGroup()
        self.add(self.anim_group)
        self.pointer = TrackPointer(nowbar_offset, h/4., 3*h/4., ps)
        self.anim_group.add(self.pointer)
        self.pitch = 60

    def on_update(self):
        self.anim_group.on_update()


class TracksDisplay(InstructionGroup):
    def __init__(self, song_data_lists, clock, ps):
        super(TracksDisplay, self).__init__()
        self.clock = clock
        self.song_data_lists = song_data_lists
        self.notes_on_screen = {}

        self.remove_list = []
        self.nowbar_offset = 150
        self.nowbar = Line(points=[self.nowbar_offset, 0, self.nowbar_offset, h], dash_offset=10)
        self.add(Color(rgb=(1, 1, 1)))
        self.add(self.nowbar)

        self.pd = PointerDisplay(self.nowbar_offset, ps)
        self.add(self.pd)
        
        self.trans = Translate()
        self.add(self.trans)

    def on_update(self) :
        self.pd.on_update()

        for trackIndex in range(len(self.song_data_lists)):
            track = self.song_data_lists[trackIndex]
            colorRGB = rainbowRGB[trackIndex]
            for (note_time, note_pitch, note_dur) in track.get_notes_in_range(self.clock.get_time(), self.clock.get_time() + 4):
                if note_time not in self.notes_on_screen:

                    notedisp = NoteBlock(note_pitch, note_dur, h/4., 3*h/4., Color(rgb=colorRGB), note_time*200 + self.nowbar_offset)
                    self.notes_on_screen[note_time] = notedisp
                    self.add(notedisp)

        for note_time in self.notes_on_screen:
            if note_time not in self.remove_list and self.clock.get_time() - note_time > 3: #note is off the screen

                self.remove_list.append(note_time)

        for note_time in self.remove_list:
            note = self.notes_on_screen[note_time]
            self.remove(note)
            self.remove_list.remove(note_time)

            del self.notes_on_screen[note_time]
        self.trans.x = -self.clock.get_time() * 200

class AudioController(object):
    def __init__(self, song_path):
        super(AudioController, self).__init__()
        self.audio = Audio(2, input_func = self.receive_audio)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)
        self.song = song_path
        melody_path = self.song + '_melody.wav'
        harmony_path = self.song + '_harmony.wav'
        self.melody_track = WaveGenerator(WaveFile(melody_path))
        self.harmony_track = WaveGenerator(WaveFile(harmony_path))
        self.mixer.add(self.melody_track)
        self.mixer.add(self.harmony_track)
        self.melody_mute = False
        self.harmony_mute = False

        self.pitch = 0
        self.input_buffers = []
        self.downsample = 1
        self.samplerate = 44100 // self.downsample
        if len( sys.argv ) > 2: self.samplerate = int(sys.argv[2])
        self.win_s = 4096 // self.downsample # fft size
        self.hop_s = 512  // self.downsample # hop size
        self.tolerance = 0.8
        self.pitch_o = pitch("yin", self.win_s, self.hop_s, self.samplerate)
        self.pitch_o.set_unit("midi")
        self.pitch_o.set_tolerance(self.tolerance)

    def receive_audio(self, frames, num_channels):
        self.input_buffers.append(frames)

    def _process_input(self):
        pass

    # start / stop the song
    def toggle(self):
        self.melody_track.play_toggle()
        self.harmony_track.play_toggle()

    def toggle_melody(self):
        if self.melody_mute:
            #unmute
            self.melody_track.set_gain(1.0)
        else:
            #mute
            self.melody_track.set_gain(0)
        self.melody_mute = not self.melody_mute


    def toggle_harmony(self):
        if self.harmony_mute:
            #unmute
            self.harmony_track.set_gain(1.0)
        else:
            #mute
            self.harmony_track.set_gain(0)
        self.harmony_mute = not self.harmony_mute

    # needed to update audio
    def on_update(self):
        self.audio.on_update()

        if len(self.input_buffers) > 0:
            pitch = self.pitch_o(self.input_buffers.pop(0)[:512])[0]
            pitch = int(round(pitch))
            if pitch != self.pitch:
                self.pitch = pitch


class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()
        self.clock = Clock()
        self.label = topleft_label()
        self.add_widget(self.label)
        self.ac = AudioController("sound_of_silence")
        self.trackdata = TrackData("melody_data.txt")
        self.trackdata2 = TrackData("harmony_data.txt")
        self.ps = ParticleSystem('../common/particle/particle.pex')     
        self.add_widget(self.ps)
        self.td = TracksDisplay([self.trackdata, self.trackdata2], self.clock, self.ps)
        self.canvas.add(self.td)

        self.harmony_detect = HarmonyDetector('minor', 63)
        self.pitch = 63
        self.melody_pitch = 63

    def on_key_down(self, keycode, modifiers):
        # play / pause toggle
        if keycode[1] == 'p':
            self.ac.toggle()
            self.clock.toggle()

        if keycode[1] == 'm':
            self.ac.toggle_melody()

        if keycode[1] == 'h':
            self.ac.toggle_harmony()

    def on_update(self) :
        self.ac.on_update()
        self.get_melody_pitch()
        if self.ac.pitch != self.pitch:
            self.pitch = self.ac.pitch
            if self.pitch != 0:
                self.td.pd.pointer.set_pitch(self.pitch)
                diff, harmony_is_valid = self.harmony_detect.check_harmony(self.melody_pitch, self.pitch)
                # print diff
                # print harmony_is_valid
                self.td.pd.pointer.change_pointer_angle(diff)
            else:
                harmony_is_valid = False
                self.td.pd.pointer.change_pointer_angle(0)
            if not harmony_is_valid:
                self.ps.stop()
            else:
                self.ps.start()
        self.td.on_update()
        self.label.text = "Melody: " + str(not self.ac.melody_mute) + "\n"
        self.label.text += "Harmony: " + str(not self.ac.harmony_mute) + "\n"

    def get_melody_pitch(self):
        time = self.clock.get_time()
        notes = self.trackdata.get_notes_in_range(time, time+0.1)
        if notes:
            melody_pitch = notes[0][1]
            self.melody_pitch = melody_pitch

run(MainWidget)


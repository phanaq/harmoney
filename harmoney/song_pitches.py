#! /usr/bin/env python

import sys
sys.path.append('..')
from common.core import *
from common.audio import *
from common.mixer import *
from common.wavegen import *
from common.wavesrc import *
from common.clock import *

from common.gfxutil import *
from aubio import source, pitch

from kivy.core.window import Window
# from kivy.graphics import Color, Line
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.graphics.instructions import InstructionGroup
from kivy.clock import Clock as kivyClock

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

# class NoteBlock(InstructionGroup):
#     def __init__(self, pos, width):
#         super(NoteBlock, self).__init__()
#         self.height = 30
#         self.width = width
#         self.pos = (pos[0], pos[1] - self.height / 2)
#         self.color = Color(0, 1, 0)
#         self.rect = Rectangle(pos=self.pos, size=(self.width, self.height))
#         self.add(self.color)
#         self.add(self.rect)

#     def on_hit(self):
#         pass

#     def on_pass(self):
#         pass

# self.notes = [] #list of tuples of (pitch, dur)



#colors for note blocks: white, pink, red, orange, yellow, green, light blue, dark blue, purple
rainbowRGB = [(1, 1, 1), (1, .4, 1), (1, 0, 0), (1, .4, 0), (1, 1, 0), (.4, 1, .2), (0, 1, 1), (0, 0, 1), (.4, 0, .8)]
# Parts 3,4
class NoteBlock(InstructionGroup): # modified from lab4
    def __init__(self, pitch, duration, floorY, ceilingY, color, xpos):
        super(NoteBlock, self).__init__()

        x = xpos
        y = np.interp(pitch, [58, 74], [floorY, ceilingY])

        # if isArp:
        #     self.color = Color(rgb = rainbowRGB[colorIndex])
        # else: #is note seq
        #     self.color = Color(rgb = (1, 1, 1))
        self.color = color
        self.color.a = .65
        #length of block is directly proportional to duration
        # self.rect = Rectangle(size = (float(duration)/480 * 120, 30), pos=(x,y))
        self.rect = Rectangle(size = (float(duration) * 200, 30), pos=(x,y))

        self.add(self.color)
        self.add(self.rect)

        # self.time = 0
        # dur = 2
        # self.alpha_anim = KFAnim((0, 1.), (dur, 0.))
        # self.pos_anim   = KFAnim((0, x, y), (dur, 0., y))

        # self.on_update(0)

    # def on_update(self, dt):
    #     self.time += dt

    #     #fading and sliding across screen
    #     self.color.a = self.alpha_anim.eval(self.time)
    #     self.rect.pos = self.pos_anim.eval(self.time)

    #     return self.alpha_anim.is_active(self.time)

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
        # self.note_dict = {4: (60, 1), 5: (62, 1), 6: (64, 1)}



        # self.barline_dict = {}
        # self.read_data(note_file, barline_file)
    # read the notes and song data. You may want to add a secondary filepath
    # argument if your barline data is stored in a different txt file.
    # def read_data(self, note_file, barline_file):
    #     note_lines = lines_from_file(note_file)
    #     bar_lines = lines_from_file(barline_file)
    #     for note_line in note_lines:
    #         tokens = tokens_from_line(note_line)
    #         time = float(tokens[0])+ .275
    #         lane = float(tokens[1])
    #         self.note_dict[time] = lane
    #     for bar_line in bar_lines:
    #         tokens = tokens_from_line(bar_line)
    #         time = float(tokens[0]) + .15
    #         lane = int(tokens[1])
    #         self.barline_dict[time] = lane

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

    # def get_notes(self):
    #     return self.notes

    def get_notes(self):
        return self.note_dict #dict w key = note times, val = (pitch, dur)

    # return a sublist of the notes that match this time slice:
    def get_notes_in_range(self, start_time, end_time):
        notes_in_range = []
        for note_time in self.note_dict:
            if note_time >= start_time and note_time <= end_time:
                notes_in_range.append((note_time, self.note_dict[note_time][0], self.note_dict[note_time][1]))
        return notes_in_range #list of gem times

# class SongData(object):
#     def __init__(self):
#         super(SongData, self).__init__()

#         # list of tuples of the form (midi value, start time, duration)
#         self.notes = []

#     # read the annotation data
#     # notes are annotated by their midi value, with periods of silence labelled by 0
#     def read_data(self, solo_file):
#         solo = open(solo_file)
#         lines = solo.readlines()

#         # for each line, remove \n and split by \t
#         for ind in range(len(lines)):
#             line = lines[ind]
#             tokens = line.strip().split("\t")

#             # 0 means silence
#             if int(tokens[1]) != 0:

#                 # get start time of next note to calculate duration
#                 next_line = lines[ind+1]
#                 next_tokens = next_line.strip().split("\t")
#                 self.notes.append((int(tokens[1]), float(tokens[0]), float(next_tokens[0]) - float(tokens[0])))

#     def get_notes(self):
#         return self.notes


class TracksDisplay(InstructionGroup):
    def __init__(self, song_data_lists, clock):
        super(TracksDisplay, self).__init__()
        self.clock = clock
        self.song_data_lists = song_data_lists
        self.notes_on_screen = {}
        # self.barlines_on_screen = []
        # self.nowbar = []
        self.remove_list = []
        self.nowbar_offset = 150
        self.nowbar = Line(points=[self.nowbar_offset, 0, self.nowbar_offset, h], dash_offset=10)
        self.add(self.nowbar)
        self.trans = Translate()
        self.add(self.trans)

    def on_update(self) :
        for trackIndex in range(len(self.song_data_lists)):
            track = self.song_data_lists[trackIndex]
            colorRGB = rainbowRGB[trackIndex]
            # print "notes in range: ", track.get_notes_in_range(self.clock.get_time(), self.clock.get_time() + 5)
            for (note_time, note_pitch, note_dur) in track.get_notes_in_range(self.clock.get_time(), self.clock.get_time() + 4):
                # print (note_time, note_pitch, note_dur)
                if note_time not in self.notes_on_screen:
                    # print "track index, note time adding: ", trackIndex, note_time
                    notedisp = NoteBlock(note_pitch, note_dur, h/4., 3*h/4., Color(rgb=colorRGB), note_time*200 + self.nowbar_offset)
                    self.notes_on_screen[note_time] = notedisp
                    self.add(notedisp)


        # for (note_pitch, note_dur) in track.get_notes_in_range(self.clock.get_time() + 1, self.clock.get_time() + 5):
        #     if note_time not in self.notes_on_screen:

        #         notedisp = noteDisplay((note_lane*w/8 + w/8, note_time*100 + 100), Color(rgb=(1, 1, 1)), self.streak)
        #         self.notes_on_screen[note_time] = notedisp
        #         self.add(notedisp)
            # else:
            #     if self.streak:
            #         self.notes_on_screen[note_time].change_to_streak()
        # self.updated += 1
        # for (barline_time, barline_lane) in self.song_data.get_barlines_in_range(self.clock.get_time(), self.clock.get_time() + 5):
        #     if barline_time not in self.barlines_on_screen:
        #         self.barlines_on_screen.append(barline_time)
        #         barlinedisp = BarLineDisplay((barline_lane*Window.width/6, barline_time*100 + 100), Color(rgb=(1, 1, 1)))
        #         self.add(barlinedisp)

        for note_time in self.notes_on_screen:
            if note_time not in self.remove_list and self.clock.get_time() - note_time > 3: #note is off the screen

                self.remove_list.append(note_time)
        # self.counter += 1
        for note_time in self.remove_list:
            note = self.notes_on_screen[note_time]
            self.remove(note)
            self.remove_list.remove(note_time)
            # print "removing note ", note_time
            del self.notes_on_screen[note_time]
        self.trans.x = -self.clock.get_time() * 200

class AudioController(object):
    def __init__(self, song_path):
        super(AudioController, self).__init__()
        self.audio = Audio(2)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)
        self.song = song_path
        melody_path = self.song + '_melody.wav'
        harmony_path = self.song + '_harmony.wav'
        self.harmony_track = WaveGenerator(WaveFile(melody_path))
        self.melody_track = WaveGenerator(WaveFile(harmony_path))
        self.mixer.add(self.melody_track)
        self.mixer.add(self.harmony_track)

    # # start / stop the song
    # def toggle(self):
    #     self.solo_track.play_toggle()
    #     self.bg_track.play_toggle()

    # # mute / unmute the solo track
    # def set_mute(self, mute):
    #     if mute:
    #         self.solo_track.set_gain(0)
    #     else:
    #         self.solo_track.set_gain(1.0)

    # # play a sound-fx (miss sound)
    # def play_sfx(self):
    #     self.mixer.add(WaveGenerator(WaveFile("../data/raspberry.wav")))

    # needed to update audio
    def on_update(self):
        self.audio.on_update()



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

class MainWidget2(BaseWidget) :
    def __init__(self):
        super(MainWidget2, self).__init__()
        self.clock = Clock()
        # self.label = topright_label()
        # self.add_widget(self.label)
        self.ac = AudioController("sound_of_silence")
        self.trackdata = TrackData("melody_data.txt")
        self.trackdata2 = TrackData("harmony_data.txt")
        # self.songdata = SongData("../data/solo_gems_final.txt", "../data/barlines.txt")
        # self.beatmatchdisplay = BeatMatchDisplay(self.songdata, self.clock)
        self.td = TracksDisplay([self.trackdata, self.trackdata2], self.clock)
        self.canvas.add(self.td)
        # self.player = Player(self.songdata, self.beatmatchdisplay, self.ac)
        

    # def on_key_down(self, keycode, modifiers):
    #     # play / pause toggle
    #     if keycode[1] == 'p':
    #         self.ac.toggle()
    #         self.clock.toggle()

    #     if keycode[1] == 'm':
    #         self.ac.set_mute(True)

    #     # button down
    #     button_idx = lookup(keycode[1], '12345', (0,1,2,3,4))
    #     if button_idx != None:
    #         # print 'down', button_idx
    #         self.player.on_button_down(button_idx)

    # def on_key_up(self, keycode):
    #     # button up
    #     button_idx = lookup(keycode[1], '12345', (0,1,2,3,4))
    #     if button_idx != None:
    #         # print 'up', button_idx
    #         self.player.on_button_up(button_idx)

    def on_update(self) :
        self.ac.on_update()
        self.td.on_update()
        # self.player.on_update()
        # self.label.text = "SCORE: " + str(self.player.score) + "\n"
        # self.label.text += "STREAK: " + str(self.player.streakcount) + "\n"
        # self.label.text += "MAX STREAK: " + str(self.player.max_streak)




run(MainWidget2)


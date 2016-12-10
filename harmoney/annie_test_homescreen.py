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
from kivy.uix.image import *

from harmony_detect import *

w = Window.width
h = Window.height

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

    def press_key(self, key):
        if key == 'p':
            self.toggle()

        if key == 'm':
            self.toggle_melody()

        if key == 'h':
            self.toggle_harmony()

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


class HomeDisplay(InstructionGroup):
    def __init__(self, trackdata):
        super(HomeDisplay, self).__init__()
        self.clock = Clock()
        self.trackdata = trackdata
        self.setUp()

    def setUp(self):
        self.add(Color(1,1,1))
        texture = Image(source='title.png').texture
        self.add(Rectangle(texture=texture, pos=((w/2.)-250,(h/2.)),size=(500,200)))

        self.add(Color(1,1,1,.5))
        self.button = ClickTangle(cpos=(w/2.,200), csize=(400,100))
        self.add(self.button)

        self.add(Color(0,0,0))
        self.middle = Rectangle(pos=((w/2.)-190,160), size=(380,80))
        self.add(self.middle)

        self.add(Color(1,1,1,.5))
        texture = Image(source='button_text.png').texture
        self.add(Rectangle(texture=texture, pos=((w/2.)-120,165), size=(240,70)))

    def click(self, pos):
        return self.button.within_bounds(pos)

    def on_update(self, dt):
        pass

class GameDisplay(InstructionGroup):
    def __init__(self, trackdata, ps):
        super(GameDisplay, self).__init__()
        self.clock = Clock()
        self.clock.stop()
        self.trackdata = trackdata
        self.ps = ps

        self.add(Color(1, 1, 1, .5))
        self.rectangle = ClickTangle(pos=(10,10), size=(50,30))
        self.add(self.rectangle)

        self.td = TracksDisplay(self.trackdata, self.clock, self.ps)
        self.add(self.td)

    def click(self, pos):
        return self.rectangle.within_bounds(pos)

    def on_update(self):
        self.td.on_update()

class Display(InstructionGroup):
    def __init__(self, trackdata, ps):
        super(Display, self).__init__()
        self.trackdata = trackdata
        self.ps = ps

        self.home_display = HomeDisplay(self.trackdata)
        self.game_display = GameDisplay(self.trackdata, self.ps)
        self.which_display = self.home_display
        self.add(self.home_display)

    def click(self, touch):
        click = self.which_display.click(touch.pos)
        if click:
            self.toggle()
            return True

    def toggle(self):
        if self.which_display == self.home_display:
            next_display = self.game_display
            self.ps.emitter_x = 120
            self.game_display.clock.start()
            self.home_display.clock.stop()
        elif self.which_display == self.game_display:
            next_display = self.home_display
            self.ps.start()
            self.game_display.clock.stop()
            self.home_display.clock.start()
        self.clear()
        self.add(next_display)   
        self.which_display = next_display   

    def on_update(self, dt):
        pass

class MainWidget2(BaseWidget) :
    def __init__(self):
        super(MainWidget2, self).__init__()

        # track data
        self.trackdata = [TrackData("melody_data.txt"), TrackData("harmony_data.txt")]
        
        # particle system
        self.ps = ParticleSystem('../common/particle/particle.pex')
        self.add_widget(self.ps)

        # display
        self.anim_group = AnimGroup()
        self.display = Display(self.trackdata, self.ps)
        self.anim_group.add(self.display)
        self.canvas.add(self.anim_group)

        # audio
        self.audio = AudioController("sound_of_silence")

        # label
        self.label = topleft_label()
        self.add_widget(self.label)

        # player
        self.player = HarmoneyPlayer(self.ps, self.display, self.audio, self.label)

    def on_touch_down(self, touch):
        self.player.on_touch_down(touch)
        
    def on_key_down(self, keycode, modifiers):
        self.player.on_key_down(keycode, modifiers)

    def on_update(self):
        self.anim_group.on_update()
        self.player.on_update()

class HarmoneyPlayer(InstructionGroup):
    def __init__(self, ps, display, audio, label):
        super(HarmoneyPlayer, self).__init__()
        self.ps = ps
        self.display = display
        self.audio = audio
        self.label = label

        self.detector = HarmonyDetector('minor', 63)
        self.pitch = self.detector.tonic
        self.melody_pitch = self.detector.tonic

        self.clock = self.display.which_display.clock
        self.pointer = self.display.game_display.td.pd.pointer

    def on_touch_down(self, touch):
        switch = self.display.click(touch)
        # print 'switch:', switch

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 'p':
            self.clock.toggle()

        self.audio.press_key(keycode[1])

    def get_melody_pitch(self):
        time = self.clock.get_time()
        notes = self.display.trackdata[0].get_notes_in_range(time, time+0.1)
        if notes:
            melody_pitch = notes[0][1]
            self.melody_pitch = melody_pitch

    def update_game_display(self):
        self.audio.on_update()
        self.get_melody_pitch()
        if self.audio.pitch != self.pitch:
            self.pitch = self.audio.pitch
            if self.pitch != 0:
                self.pointer.set_pitch(self.pitch)
                diff, harmony_is_valid = self.detector.check_harmony(self.melody_pitch, self.pitch)
                self.pointer.change_pointer_angle(diff)
            else:
                harmony_is_valid = False
                self.pointer.change_pointer_angle(0)
            if not harmony_is_valid:
                self.ps.stop()
            else:
                self.ps.start()
        self.display.game_display.on_update()

    def update_home_display(self):
        xpos, ypos = Window.mouse_pos
        self.ps.emitter_x = xpos
        self.ps.emitter_y = ypos

    def on_update(self):
        if self.display.which_display == self.display.game_display:
            
            self.update_game_display()
        else:
            self.update_home_display()
            

run(MainWidget2)

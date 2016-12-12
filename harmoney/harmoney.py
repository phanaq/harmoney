#! /usr/bin/env python

import sys
sys.path.append('..')
from common.core import *
from common.audio import *
from common.gfxutil import *
from common.harmony_detect import *
from common.mixer import *
from common.wavegen import *
from common.wavesrc import *
from common.clock import *
from common.kivyparticle import ParticleSystem

from aubio import source, pitch
from random import randint

from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.graphics.instructions import InstructionGroup
from kivy.clock import Clock as kivyClock
from kivy.uix.image import Image

w = Window.width
h = Window.height

#colors for note blocks: white, pink, red, orange, yellow, green, light blue, dark blue, purple
rainbowRGB = [(1, 1, 1), (1, .4, 1), (1, 0, 0), (1, .4, 0), (1, 1, 0), (.4, 1, .2), (0, 1, 1), (0, 0, 1), (.4, 0, .8)]


class NoteBlock(InstructionGroup):
    def __init__(self, pitch, duration, floorY, ceilingY, color, xpos, height, mel, harm):
        super(NoteBlock, self).__init__()
        self.x = xpos
        self.y = np.interp(pitch, [50, 86], [floorY, ceilingY])

        self.pitch = pitch
        self.color = color
        self.on_color = color.rgb
        self.off_color = (.3, .3, .3)
        self.color.a = .5

        self.mel = mel
        self.harm = harm
        self.highlighted = False

        self.rect = Rectangle(size = (float(duration) * 200, height), pos=(self.x,self.y-height/2.))

        self.add(self.color)
        self.add(self.rect)

    def fade_out(self):
        if not self.highlighted:
            self.color.rgb = self.off_color

    def fade_in(self):
        if not self.highlighted:
            self.color.rgb = self.on_color

    def highlight(self):
        print "HIGHLIGHTING"
        self.color.rgb = (.4, .8, .9)
        self.highlighted = True

    def on_update(self):
        pass


class Star(CEllipse):
    def __init__(self):
        # get random position for CEllipse
        rand_pos = (randint(0, Window.width), randint(0, Window.height))
        super(Star, self).__init__(cpos=self.pos, csize=(5, 5), segments=6)

        # animate star to twinkle once and then die
        duration = randint(1, 5)
        self.radius_anim = KFAnim((0, 0), (duration/2., 3), (duration, 0))
        self.pos = np.array(rand_pos, dtype=np.float64)
        self.vel = np.array((0, 0), dtype=np.float64)     
        self.time = 0

        self.on_update(0)

    def on_update(self, dt):
        # animate radius
        r = self.radius_anim.eval(self.time)
        self.csize = (2*r, 2*r)

        # integrate vel to get pos
        self.pos += self.vel * dt

        self.time += dt
        return self.radius_anim.is_active(self.time)


class TrackData(object):
    def __init__(self, solo_file, offset=0):  
        super(TrackData, self).__init__()
        self.offset = offset
        self.notes = []
        self.note_dict = {}
        self.read_data(solo_file)
        for note in self.notes:
            start_time = note[1]
            pitch = note[0]
            dur = note[2]
            words = note[3]
            self.note_dict[start_time] = (pitch, dur, words)

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
                if len(tokens) == 2:
                    self.notes.append((int(tokens[1])+self.offset, float(tokens[0])+self.offset*10**-6, float(next_tokens[0]) - float(tokens[0]), None))
                elif len(tokens) == 3:
                    self.notes.append((int(tokens[1])+self.offset, float(tokens[0])+self.offset*10**-6, float(next_tokens[0]) - float(tokens[0]), tokens[2]))

    def get_notes(self):
        return self.note_dict #dict w key = note times, val = (pitch, dur)

    # return a sublist of the notes that match this time slice:
    def get_notes_in_range(self, start_time, end_time):
        notes_in_range = []
        for note_time in self.note_dict:
            if note_time >= start_time and note_time <= end_time:
                notes_in_range.append((note_time, self.note_dict[note_time][0], self.note_dict[note_time][1], self.note_dict[note_time][2]))
        return notes_in_range #list of gem times


class PointerDisplay(InstructionGroup):
    def __init__(self, nowbar_offset, ps):
        super(PointerDisplay, self).__init__()
        self.anim_group = AnimGroup()
        self.add(self.anim_group)
        self.pointer = CatPointer(nowbar_offset, h/4., 3*h/4., ps)
        self.anim_group.add(self.pointer)
        self.pitch = 60

    def on_update(self):
        self.anim_group.on_update()
        return self.pointer.ypos


class TracksDisplay(InstructionGroup):
    def __init__(self, song_data_lists, clock, ps, lyrics, stars):
        super(TracksDisplay, self).__init__()
        self.clock = clock
        self.lyrics = lyrics
        self.song_data_lists = song_data_lists
        self.notes_on_screen = {}

        self.remove_list = []
        self.nowbar_offset = 150
        self.nowbar = Line(points=[self.nowbar_offset, 0, self.nowbar_offset, h], dash_offset=10)
        self.add(Color(rgb=(1, 1, 1)))
        self.add(self.nowbar)

        self.pd = PointerDisplay(self.nowbar_offset, ps)
        self.add(self.pd)

        self.stars = stars
        self.add(self.stars)

        self.trans = Translate()
        self.add(self.trans)

    def on_update(self, melody_is_playing, harmony_is_playing, pitch, valid):
        pointer_ypos = self.pd.on_update()

        for trackIndex in range(len(self.song_data_lists)):
            track = self.song_data_lists[trackIndex]
            colorRGB = rainbowRGB[trackIndex]
            for (note_time, note_pitch, note_dur, words) in track.get_notes_in_range(self.clock.get_time(), self.clock.get_time() + 4):
                if note_time not in self.notes_on_screen:

                    if trackIndex == 0:
                        notedisp = NoteBlock(note_pitch, note_dur, 10, h-10, Color(rgb=colorRGB), note_time*200 + self.nowbar_offset, 25, True, False)
                    elif trackIndex == 1:
                        notedisp = NoteBlock(note_pitch, note_dur, 10, h-10, Color(rgb=colorRGB), note_time*200 + self.nowbar_offset, 25, False, True)
                    else:
                        notedisp = NoteBlock(note_pitch, note_dur, 10, h-10, Color(rgb=(.3, .3, .3)), note_time*200 + self.nowbar_offset, 5, False, False)

                    if words:
                        self.lyrics.text = words
                    self.notes_on_screen[note_time] = notedisp
                    self.add(notedisp)

        # fade out notes when mel or harm is false (not playing)
        for note_time in self.notes_on_screen:
            note = self.notes_on_screen[note_time]
            if note.mel:
                if melody_is_playing:
                    note.fade_in()
                else:
                    note.fade_out()
            elif note.harm:
                if harmony_is_playing:
                    note.fade_in()
                else:
                    note.fade_out()


        # if the harmony is valid, highlight something close in pitch
        # if valid:
        #     note_options = []
        #     for note_time in self.notes_on_screen:
        #         note = self.notes_on_screen[note_time]
        #         if abs(self.nowbar_offset - (note.x - self.clock.get_time()*200)) < 20:
        #             note = self.notes_on_screen[note_time]
        #             note_options.append(note)
        #     note_options = sorted(note_options, key=lambda x: abs(pitch - x.pitch))
        #     if len(note_options) > 0:
        #         note_options[0].highlight()

        # if the harmony is valid, highlight something close to the pointer
        if valid:
            note_options = []
            for note_time in self.notes_on_screen:
                note = self.notes_on_screen[note_time]
                if abs(self.nowbar_offset - (note.x - self.clock.get_time()*200)) < 5:
                    note = self.notes_on_screen[note_time]
                    note_options.append(note)
            note_options = sorted(note_options, key=lambda x: abs(pointer_ypos - note.y))
            if len(note_options) > 0:
                note_options[0].highlight()

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

        self.use_microphone = True

        self.setUp()

    def setUp(self):
    	if self.use_microphone:
	        self.pitch = 0
	        self.input_buffers = []
	        self.downsample = 1
	        self.samplerate = 44100 // self.downsample
	        if len( sys.argv ) > 2: self.samplerate = int(sys.argv[2])
	        self.win_s = 4096 // self.downsample # fft size
	        self.hop_s = 512  // self.downsample # hop size
	        self.tolerance = 0.9
	        self.pitch_o = pitch("yinfft", self.win_s, self.hop_s, self.samplerate)
	        self.pitch_o.set_unit("midi")
	        self.pitch_o.set_tolerance(self.tolerance)
        else:
	        # test file input
	        self.pitch = 0
	        self.filename = 'major_scale.wav'
	        # self.mixer.add(WaveGenerator(WaveFile(self.filename), loop=False))
	        self.downsample = 1
	        self.samplerate = 44100 // self.downsample
	        self.win_s = 4096 // self.downsample # fft size
	        self.hop_s = 512  // self.downsample # hop size

	        self.s = source(self.filename, self.samplerate, self.hop_s)
	        self.samplerate = self.s.samplerate
	        self.tolerance = 0.9
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

    def on_update(self):
        self.audio.on_update()

        if self.use_microphone:
	        if len(self.input_buffers) > 0:
	            pitch = self.pitch_o(self.input_buffers.pop(0)[:512])[0]
	            print pitch
	            pitch = int(round(pitch))
	            print str(pitch) + '/n'
	            if pitch != self.pitch:
	                self.pitch = pitch
        else:
	        samples, read = self.s()
	        pitch = self.pitch_o(samples)[0]
	        pitch = int(round(pitch))
	        if pitch != self.pitch and pitch != 0:
	            self.pitch = pitch


class HomeDisplay(InstructionGroup):
    def __init__(self):
        super(HomeDisplay, self).__init__()
        self.clock = Clock()
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
    def __init__(self, trackdata, ps, lyrics, stars):
        super(GameDisplay, self).__init__()
        self.trackdata = trackdata
        self.ps = ps
        self.lyrics = lyrics

        self.clock = Clock()
        self.clock.stop()

        self.add(Color(1, 1, 1, .5))
        self.rectangle = ClickTangle(pos=(10,10), size=(50,30))
        self.add(self.rectangle)

        self.td = TracksDisplay(self.trackdata, self.clock, self.ps, self.lyrics, stars)
        self.add(self.td)

    def click(self, pos):
        return self.rectangle.within_bounds(pos)

    def on_update(self, melody_is_playing, harmony_is_playing, pitch, valid):
        self.td.on_update(melody_is_playing, harmony_is_playing, pitch, valid)

class Display(InstructionGroup):
    def __init__(self, trackdata, ps, lyrics):
        super(Display, self).__init__()
        self.trackdata = trackdata
        self.ps = ps
        self.lyrics = lyrics

        # add stars to background
        self.add(Color(1,1,1))
        self.objects = AnimGroup()
        self.add(self.objects)
        self.num_stars = 300
        for i in range(self.num_stars):
            self.objects.add(Star())

        self.home_display = HomeDisplay()
        self.game_display = GameDisplay(self.trackdata, self.ps, self.lyrics, self.objects)
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
    	self.objects.on_update()
    	if self.objects.size() < self.num_stars:
            for i in range(self.num_stars - self.objects.size()):
                self.objects.add(Star())

class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()
        # add tracks
        self.melody_track = TrackData("melody_data.txt", offset=1)
        self.harmony_track = TrackData("harmony_data.txt", offset=1)
        self.third_up = TrackData("melody_data.txt", offset=5)
        self.third_down = TrackData("melody_data.txt", offset=-3)
        self.fifth_up = TrackData("melody_data.txt", offset=8)
        self.fifth_down = TrackData("melody_data.txt", offset=-6)
        trackdata = [
        	self.melody_track, 
        	self.harmony_track, self.third_up, 
        	self.third_down, 
        	self.fifth_up, 
        	self.fifth_down
    	]

    	# add lyrics
        self.lyrics = Label(
        	text="Hello darkness, my old friend", 
        	font_size=32, 
        	pos=(w/2 - 50, 20))
        self.add_widget(self.lyrics)

    	# particle system
        self.ps = ParticleSystem('../common/particle/particle.pex')
        self.add_widget(self.ps)

        # display
        self.anim_group = AnimGroup()
        self.display = Display(trackdata, self.ps, self.lyrics)
        self.anim_group.add(self.display)
        self.canvas.add(self.anim_group)

        self.audio = AudioController("sound_of_silence")

        self.label = topleft_label()

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

        self.melody_playing = True
        self.harmony_playing = True

    def on_touch_down(self, touch):
        switch = self.display.click(touch)

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 'p':
        	self.audio.toggle()
        	clock = self.display.which_display.clock
        	clock.toggle()

        if keycode[1] == 'm':
        	self.audio.toggle_melody()
        	self.melody_playing = not self.melody_playing

        if keycode[1] == 'h':
            self.audio.toggle_harmony()
            self.harmony_playing = not self.harmony_playing

    def get_melody_pitch(self):
        time = self.clock.get_time()
        notes = self.display.trackdata[0].get_notes_in_range(time, time+0.1)
        if notes:
            melody_pitch = notes[0][1]
            self.melody_pitch = melody_pitch

    def update_game_display(self):
        self.audio.on_update()
        self.get_melody_pitch()
        harmony_is_valid = False
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
        self.display.game_display.on_update(self.melody_playing, self.harmony_playing, self.pitch, harmony_is_valid)

    def update_home_display(self):
        xpos, ypos = Window.mouse_pos
        self.ps.emitter_x = xpos
        self.ps.emitter_y = ypos

    def on_update(self):
        if self.display.which_display == self.display.game_display:
            self.update_game_display()
        else:
            self.update_home_display()
            
run(MainWidget)

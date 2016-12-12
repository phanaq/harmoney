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
from common.note import *
from common.kivyparticle import ParticleSystem

from aubio import source, pitch
from collections import Counter
from random import randint

from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.graphics import PushMatrix, PopMatrix, Translate, Rotate
from kivy.graphics.instructions import InstructionGroup
from kivy.clock import Clock as kivyClock
from kivy.uix.image import Image

w = Window.width
h = Window.height

#colors for note blocks: red, orange, white, pink, yellow-green, light blue, light purple
rainbowRGB = [(1, .4, .4), (1, .6, .2), (.4, .8, .9), (1, .4, 1), (.8, 1, .4), (.4, .85, 1), (.8, .6, 1)]
cpRainbow = [(1, .4, .4), (1, .6, .2), (.8, 1, .4), (.4, .85, 1), (.8, .6, 1)]

class NoteBlock(InstructionGroup):
    def __init__(self, pitch, duration, floorY, ceilingY, color, xpos, height, mel, harm, track):
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
        self.track = track

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
        self.color.rgb = (1, 0.843137, 0)
        self.highlighted = True

    def activate(self):
        self.color.a = 1

    def deactivate(self):
        self.color.a = 0.5

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
        self.scale = Scale('minor', 63)
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

                pitch_no_offset = int(tokens[1])+1
                if self.offset == 0:
                    pitch = pitch_no_offset
                else:
                    pitch = self.scale.get_interval_midi(pitch_no_offset, self.offset)

                if len(tokens) == 2:
                    self.notes.append(
                        (pitch, # pitch int
                        float(tokens[0])+self.offset*10**-6, # start time
                        float(next_tokens[0]) - float(tokens[0]), 
                        None))
                elif len(tokens) == 3:
                    self.notes.append(
                        (pitch, 
                        float(tokens[0])+self.offset*10**-6, 
                        float(next_tokens[0]) - float(tokens[0]), 
                        tokens[2]))

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
    def __init__(self, nowbar_offset, ps, floorY, ceilingY):
        super(PointerDisplay, self).__init__()
        self.anim_group = AnimGroup()
        self.add(self.anim_group)
        self.pointer = CatPointer(nowbar_offset, floorY, ceilingY, ps)
        self.anim_group.add(self.pointer)
        self.pitch = 60

    def on_update(self):
        self.anim_group.on_update()
        return self.pointer.ypos

checkpoint_times = [(0,0), (37.5921020508, 1655296), (72.140171051, 3179008), (106.991501093, 4715008), (141.582692146, 6240256)]

class CheckpointDisplay(InstructionGroup):
    def __init__(self, center_x, y, length, checkpoints, clock):
        super(CheckpointDisplay, self).__init__()
        self.clock = clock
        self.length = length
        self.y = y
        self.start_x = center_x - self.length/2.0
        self.end_x = center_x + self.length/2.0
        self.add(Color(1, 1, 1))
        self.cp_bar = Line(points=[self.start_x, self.y, self.end_x, self.y])
        self.add(self.cp_bar)
        self.cur_rel_pos = 0 #fraction of song played
        self.total_song_length = 186.0
        self.checkpoint_times = checkpoints
        self.colorIndex = 0
        self.add(Color(0, 0, 1))
        for (time, frame) in self.checkpoint_times:
            cp = CEllipse(cpos = (time/self.total_song_length * self.length + self.start_x, self.y), size=(10, 10))
            color = Color(rgb=cpRainbow[self.colorIndex])
            self.add(color)
            self.add(cp)
            self.colorIndex += 1

        self.add(Color(1, 1, 1))
        star_texture = Image(source='star.png').texture
        star = Rectangle(texture=star_texture, pos = (self.length + self.start_x - 10, self.y - 10), size=(20, 20))
        self.add(star)
        self.pos_disp = CEllipse(cpos = (self.cur_rel_pos * self.length + self.start_x, self.y), size=(10, 10))
        
        self.add(self.pos_disp)
    
    def on_update(self):
        now_time = self.clock.get_time()
        if now_time > self.total_song_length:
            now_time = self.total_song_length
        self.cur_rel_pos = now_time/self.total_song_length
        self.pos_disp.cpos = (self.cur_rel_pos * self.length + self.start_x, self.y)

class TracksDisplay(InstructionGroup):
    def __init__(self, song_data_lists, clock, ps, lyrics, stars):
        super(TracksDisplay, self).__init__()
        self.clock = clock
        self.lyrics = lyrics
        self.song_data_lists = song_data_lists
        self.notes_on_screen = {}

        self.floorY = 10
        self.ceilingY = h-10

        self.remove_list = []
        self.nowbar_offset = 150
        self.nowbar = Line(points=[self.nowbar_offset, 0, self.nowbar_offset, h], dash_offset=10)
        self.add(Color(rgb=(1, 1, 1)))
        self.add(self.nowbar)

        self.pd = PointerDisplay(self.nowbar_offset, ps, self.floorY, self.ceilingY)
        self.add(self.pd)

        self.stars = stars
        self.add(self.stars)

        self.trans = Translate()
        self.add(self.trans)

    def on_update(self, playing_tracks, selected_track, pitch, valid):
        pointer_ypos = self.pd.on_update()

        # self.lyrics.text = str(pitch)

        for trackIndex in range(len(self.song_data_lists)):
            track = self.song_data_lists[trackIndex]
            colorRGB = rainbowRGB[trackIndex]
            for (note_time, note_pitch, note_dur, words) in track.get_notes_in_range(self.clock.get_time(), self.clock.get_time() + 4):
                if note_time not in self.notes_on_screen:

                    if trackIndex == 2:
                        notedisp = NoteBlock(note_pitch, note_dur, self.floorY, self.ceilingY, Color(rgb=colorRGB), note_time*200 + self.nowbar_offset, 25, True, False, trackIndex)
                    elif trackIndex == 3:
                        notedisp = NoteBlock(note_pitch, note_dur, self.floorY, self.ceilingY, Color(rgb=colorRGB), note_time*200 + self.nowbar_offset, 25, False, True, trackIndex)
                    else:
                        notedisp = NoteBlock(note_pitch, note_dur, self.floorY, self.ceilingY, Color(rgb=(.5, .9, .3)), note_time*200 + self.nowbar_offset, 5, False, False, trackIndex)

                    if words:
                        self.lyrics.text = words
                    self.notes_on_screen[note_time] = notedisp
                    self.add(notedisp)

        # fade out notes when mel or harm is false (not playing)
        for note_time in self.notes_on_screen:
            note = self.notes_on_screen[note_time]
            if playing_tracks[note.track]:
                # print note.track
                note.fade_in()
            elif note.mel or note.harm:
                note.deactivate()
            else:
                note.fade_out()

        if pitch != 0:
            for note_time in self.notes_on_screen:
                note = self.notes_on_screen[note_time]
                if abs(self.nowbar_offset - (note.x - self.clock.get_time()*200)) < 5:
                    if note.track == selected_track:
                        note.highlight()

        for note_time in self.notes_on_screen:
            note = self.notes_on_screen[note_time]
            if note.track == selected_track:
                note.activate()
            else:
                note.deactivate()

        # # if the harmony is valid, highlight something close in pitch
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
        # if valid:
        #     note_options = []
        #     for note_time in self.notes_on_screen:
        #         note = self.notes_on_screen[note_time]
        #         if abs(self.nowbar_offset - (note.x - self.clock.get_time()*200)) < 5:
        #             note = self.notes_on_screen[note_time]
        #             note_options.append(note)
        #     note_options = sorted(note_options, key=lambda x: abs(pointer_ypos - note.y))
        #     if len(note_options) > 0:
        #         note_options[0].highlight()

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
	        self.smoothed_pitch = 0
	        self.pitch_window_size = 30
	        self.previous_pitches = []
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
    	# 63 66 70 68
        self.audio.on_update()

        if self.use_microphone:
        	if len(self.input_buffers) > 0:
        		detected_pitch = self.pitch_o(self.input_buffers.pop(0)[:512])[0]
        		pitch = int(round(detected_pitch))
        		self.previous_pitches.append(pitch)
        		if len(self.previous_pitches) > self.pitch_window_size:
        			self.previous_pitches.pop(0)
    			if pitch != self.pitch:
    				self.pitch = pitch
			pitch_counter = Counter(self.previous_pitches)
			cur_pitch = self.pitch
			most_common_pitches = pitch_counter.most_common()
			if len(most_common_pitches) > 0:
				most_common_pitch = most_common_pitches[0][0]
				if cur_pitch == most_common_pitch:
					self.smoothed_pitch = cur_pitch
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

        self.cp_display = CheckpointDisplay(w/2., h - 50, 3*w/5, checkpoint_times, self.clock)
        self.add(self.cp_display)

        self.add(Color(1, 1, 1, .5))
        self.rectangle = ClickTangle(pos=(10,10), size=(50,30))
        self.add(self.rectangle)

        self.td = TracksDisplay(self.trackdata, self.clock, self.ps, self.lyrics, stars)
        self.add(self.td)

    def click(self, pos):
        return self.rectangle.within_bounds(pos)

    def on_update(self, playing_tracks, selected_track, pitch, valid):
        self.td.on_update(playing_tracks, selected_track, pitch, valid)
        self.cp_display.on_update()

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
        self.melody_track = TrackData("melody_data.txt")
        self.harmony_track = TrackData("harmony_data.txt")
        self.third_up = TrackData("melody_data.txt", offset=2)
        self.third_down = TrackData("melody_data.txt", offset=-5)
        self.fifth_up = TrackData("melody_data.txt", offset=4)
        self.fifth_down = TrackData("melody_data.txt", offset=-3)
        self.trackdata = [
            self.fifth_up,
            self.third_up,
            self.melody_track, 
            self.harmony_track,
            self.fifth_down,
            self.third_down,
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

        # score
        # self.score_label = topright_label()
        # self.add_widget(self.score_label)

        # display
        self.anim_group = AnimGroup()
        self.display = Display(self.trackdata, self.ps, self.lyrics)
        self.anim_group.add(self.display)
        self.canvas.add(self.anim_group)

        self.audio = AudioController("sound_of_silence")

        self.label = topleft_label()

        self.player = HarmoneyPlayer(self.ps, self.display, self.audio)

    def on_touch_down(self, touch):
        self.player.on_touch_down(touch)
        
    def on_key_down(self, keycode, modifiers):
        self.player.on_key_down(keycode, modifiers)
        if keycode[1] == 'm':
            self.player.playing_tracks[self.player.selected_track] = not self.player.playing_tracks[self.player.selected_track]

    def on_update(self):
        self.anim_group.on_update()
        self.player.on_update()
        now_time = self.display.game_display.clock.get_time()
        i = self.player.selected_track
        if not self.player.explode:
            if self.player.playing_tracks[i]:
                for note in self.trackdata[i].get_notes_in_range(now_time, now_time + 2):
                    if abs(now_time - note[0]) < .025:
                        new_note = NoteGenerator(note[1], 0.5, note[2])
                        self.audio.mixer.add(new_note)
        else:
            for i in range(len(self.player.playing_tracks)):
                if self.player.playing_tracks[i]:
                    for note in self.trackdata[i].get_notes_in_range(now_time, now_time + 2):
                        if abs(now_time - note[0]) < .025:
                            new_note = NoteGenerator(note[1], 0.5, note[2])
                            self.audio.mixer.add(new_note)

class HarmoneyPlayer(InstructionGroup):
    def __init__(self, ps, display, audio):
        super(HarmoneyPlayer, self).__init__()
        self.ps = ps
        self.display = display
        self.audio = audio
        self.score = 0
        self.index = 0 #index of most recent checkpoint
        self.checkpoint_times = display.game_display.cp_display.checkpoint_times

        self.detector = HarmonyDetector('minor', 63)
        self.display_pitch = self.detector.tonic
        self.melody_pitch = self.detector.tonic

        self.octave_offsets = []
        self.octave_offset = 0

        self.clock = self.display.which_display.clock
        self.pointer = self.display.game_display.td.pd.pointer

        self.playing_tracks = [False, False, False, False, False, False]

        self.selected_track = 2
        self.track_pitch = self.detector.tonic
        self.pointer.set_pitch(self.track_pitch)

        self.melody_playing = True
        self.harmony_playing = True
        self.harmony_is_valid = False

        self.moved = False
        self.explode = False

    def on_touch_down(self, touch):
        switch = self.display.click(touch)

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 'p':
        	self.audio.toggle()
        	clock = self.display.which_display.clock
        	clock.toggle()

        if keycode[1] == 'left':
            if self.index > 0:
                self.index -= 1
            else:
                self.index = 0
            self.clock.set_time(self.checkpoint_times[self.index][0])
            self.audio.melody_track.frame = self.checkpoint_times[self.index][1]
            self.audio.harmony_track.frame = self.checkpoint_times[self.index][1]

        if keycode[1] == 'right':
            if self.index < 4:
                self.index += 1
            self.clock.set_time(self.checkpoint_times[self.index][0])
            self.audio.melody_track.frame = self.checkpoint_times[self.index][1]
            self.audio.harmony_track.frame = self.checkpoint_times[self.index][1]

        if keycode[1] == 'up':
            if self.selected_track > 0:
                old_playing = self.playing_tracks[self.selected_track]
                self.playing_tracks[self.selected_track] = False
                self.selected_track -= 1
                self.playing_tracks[self.selected_track] = True and old_playing or not self.moved
            self.moved = True

        if keycode[1] == 'down':
            if self.selected_track < 5:
                old_playing = self.playing_tracks[self.selected_track]
                self.playing_tracks[self.selected_track] = False
                self.selected_track += 1
                self.playing_tracks[self.selected_track] = True and old_playing or not self.moved
            self.moved = True

        if keycode[1] == 'spacebar':
            self.explode = not self.explode
            if self.explode:
                print "self.explode"
                for i in range(6):
                    self.playing_tracks[i] = True
            else:
                for i in range(6):
                    self.playing_tracks[i] = False
            self.moved = True
            

        button_idx = lookup(keycode[1], '12345', (0,1,2,3,4))
        if button_idx != None:
            self.index = button_idx
            self.clock.set_time(self.checkpoint_times[self.index][0])
            self.audio.melody_track.frame = self.checkpoint_times[self.index][1]
            self.audio.harmony_track.frame = self.checkpoint_times[self.index][1]

        # button_idx = lookup(keycode[1], 'asdfgh', (0,1,2,3,4,5))
        # if button_idx != None:
        #     self.playing_tracks[button_idx] = not self.playing_tracks[button_idx]

    def get_melody_pitch(self):
        time = self.clock.get_time()
        notes = self.display.trackdata[0].get_notes_in_range(time, time+0.1)
        if notes:
            melody_pitch = notes[0][1]
            self.melody_pitch = melody_pitch

    def get_track_pitch(self, index):
        time = self.clock.get_time()
        notes = self.display.trackdata[index].get_notes_in_range(time, time+0.1)
        if notes:
            pitch = notes[0][1]
            self.track_pitch = pitch

    def update_game_display(self):
        self.audio.on_update()
        self.get_melody_pitch()
        harmony_is_valid = False
        
        old_pitch = self.track_pitch
        self.get_track_pitch(self.selected_track)

        if old_pitch != self.track_pitch:
            self.pointer.set_pitch(self.track_pitch)

        cur_pitch_is_valid = self.harmony_is_valid
        pitch = self.audio.smoothed_pitch

        if pitch != 0: 
            self.ps.start()
            self.score += 10
        else:
            self.ps.stop()

        if pitch != self.display_pitch:
            self.display_pitch = pitch
            if self.display_pitch != 0:

                diff, harmony_is_valid = self.detector.check_harmony(self.melody_pitch, self.display_pitch)
                # self.pointer.change_pointer_angle(diff)
            else:
                harmony_is_valid = False
                # self.pointer.change_pointer_angle(0)
            # if not harmony_is_valid:
            #     self.ps.stop()
            # else:
            #     self.ps.start()
                # self.score += 10

        else:
            harmony_is_valid = cur_pitch_is_valid
        self.harmony_is_valid = harmony_is_valid
        self.display.game_display.on_update(self.playing_tracks, self.selected_track, self.display_pitch, harmony_is_valid)


    def update_home_display(self):
        xpos, ypos = Window.mouse_pos
        self.ps.emitter_x = xpos
        self.ps.emitter_y = ypos

    def on_update(self):
        if self.display.which_display == self.display.game_display:
            if self.clock != self.display.game_display.clock:
                self.clock = self.display.game_display.clock
            self.update_game_display()
        else:
            self.update_home_display()
            
run(MainWidget)

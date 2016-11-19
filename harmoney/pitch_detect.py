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


# if len(sys.argv) < 2:
#     print("Usage: %s <filename> [samplerate]" % sys.argv[0])
#     sys.exit(1)

# filename = sys.argv[1]
# filename = "superstition.wav"


# downsample = 1
# samplerate = 44100 // downsample
# if len( sys.argv ) > 2: samplerate = int(sys.argv[2])

# win_s = 4096 // downsample # fft size
# hop_s = 512  // downsample # hop size

# s = source(filename, samplerate, hop_s)
# samplerate = s.samplerate

# tolerance = 0.8

# pitch_o = pitch("yin", win_s, hop_s, samplerate)
# pitch_o.set_unit("midi")
# pitch_o.set_tolerance(tolerance)

# pitches = []
# confidences = []

# # total number of frames read
# total_frames = 0
# while True:
#     samples, read = s()
#     pitch = pitch_o(samples)[0]
#     #pitch = int(round(pitch))
#     confidence = pitch_o.get_confidence()
#     #if confidence < 0.8: pitch = 0.
#     print("%f %f %f" % (total_frames / float(samplerate), pitch, confidence))
#     pitches += [pitch]
#     confidences += [confidence]
#     total_frames += read
#     if read < hop_s: break

if 0: sys.exit(0)
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
        self.audio = Audio(2)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)
        self.label = topleft_label()
        self.add_widget(self.label)
        
        self.staff = Staff(100, 50)
        self.canvas.add(self.staff)
        self.setup()
    def setup(self):
        self.filename = sys.argv[1]
        # self.filename = "middle_c.wav"
        self.mixer.add(WaveGenerator(WaveFile(self.filename)))
        # print "filename: ", self.filename
        self.downsample = 1
        self.samplerate = 44100 // self.downsample
        if len( sys.argv ) > 2: self.samplerate = int(sys.argv[2])

        self.win_s = 4096 // self.downsample # fft size
        self.hop_s = 512  // self.downsample # hop size

        self.s = source(self.filename, self.samplerate, self.hop_s)
        print "s", self.s
        self.samplerate = self.s.samplerate

        self.tolerance = 0.8

        self.pitch_o = pitch("yin", self.win_s, self.hop_s, self.samplerate)
        self.pitch_o.set_unit("midi")
        self.pitch_o.set_tolerance(self.tolerance)

        self.pitches = []
        self.confidences = []

        # total number of frames read
        self.total_frames = 0
    def on_update(self):
        # print "total frames: ", self.total_frames
        # print s()
        self.audio.on_update()
        samples, read = self.s()
        pitch = self.pitch_o(samples)[0]
        pitch = int(round(pitch))
        confidence = self.pitch_o.get_confidence()
        #if confidence < 0.8: pitch = 0.
        print("%f %f %f" % (self.total_frames / float(self.samplerate), pitch, confidence))
        self.pitches += [pitch]
        self.confidences += [confidence]
        self.total_frames += read
        # if read < hop_s: break
        self.label.text = str(pitch)

run(MainWidget)
# #print pitches
# import os.path
# from numpy import array, ma
# import matplotlib.pyplot as plt
# from demo_waveform_plot import get_waveform_plot, set_xlabels_sample2time

# skip = 1

# pitches = array(pitches[skip:])
# confidences = array(confidences[skip:])
# times = [t * hop_s for t in range(len(pitches))]

# fig = plt.figure()

# ax1 = fig.add_subplot(311)
# ax1 = get_waveform_plot(filename, samplerate = samplerate, block_size = hop_s, ax = ax1)
# plt.setp(ax1.get_xticklabels(), visible = False)
# ax1.set_xlabel('')

# def array_from_text_file(filename, dtype = 'float'):
#     filename = os.path.join(os.path.dirname(__file__), filename)
#     return array([line.split() for line in open(filename).readlines()],
#         dtype = dtype)

# ax2 = fig.add_subplot(312, sharex = ax1)
# ground_truth = os.path.splitext(filename)[0] + '.f0.Corrected'
# if os.path.isfile(ground_truth):
#     ground_truth = array_from_text_file(ground_truth)
#     true_freqs = ground_truth[:,2]
#     true_freqs = ma.masked_where(true_freqs < 2, true_freqs)
#     true_times = float(samplerate) * ground_truth[:,0]
#     ax2.plot(true_times, true_freqs, 'r')
#     ax2.axis( ymin = 0.9 * true_freqs.min(), ymax = 1.1 * true_freqs.max() )
# # plot raw pitches
# ax2.plot(times, pitches, '.g')
# # plot cleaned up pitches
# cleaned_pitches = pitches
# #cleaned_pitches = ma.masked_where(cleaned_pitches < 0, cleaned_pitches)
# #cleaned_pitches = ma.masked_where(cleaned_pitches > 120, cleaned_pitches)
# cleaned_pitches = ma.masked_where(confidences < tolerance, cleaned_pitches)
# ax2.plot(times, cleaned_pitches, '.-')
# #ax2.axis( ymin = 0.9 * cleaned_pitches.min(), ymax = 1.1 * cleaned_pitches.max() )
# #ax2.axis( ymin = 55, ymax = 70 )
# plt.setp(ax2.get_xticklabels(), visible = False)
# ax2.set_ylabel('f0 (midi)')

# # plot confidence
# ax3 = fig.add_subplot(313, sharex = ax1)
# # plot the confidence
# ax3.plot(times, confidences)
# # draw a line at tolerance
# ax3.plot(times, [tolerance]*len(confidences))
# ax3.axis( xmin = times[0], xmax = times[-1])
# ax3.set_ylabel('condidence')
# set_xlabels_sample2time(ax3, times[-1], samplerate)
# plt.show()
# #plt.savefig(os.path.basename(filename) + '.svg')

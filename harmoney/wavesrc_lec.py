# wavegen - Lecture file

import numpy as np
import wave
from common.audio import kSampleRate


# a generator that reads a file and can play it back
class WaveFileGenerator(object):
    def __init__(self, filepath):
        super(WaveFileGenerator, self).__init__()

        self.wave = wave.open(filepath)
        self.num_channels, self.sampwidth, self.sr, self.end, \
           comptype, compname = self.wave.getparams()

        # for now, we will only accept 16 bit files at 44k
        assert(self.sampwidth == 2)
        assert(self.sr == 44100)

        # for testing end of file...
        # self.wave.setpos(int(4.35 * 60 * 44100))

    def generate(self, num_frames, num_channels) :
        assert(self.num_channels == num_channels)

        # get the raw data from wave file as a byte string.
        # will return num_frames, or less if too close to end of file
        raw_bytes = self.wave.readframes(num_frames)

        # convert raw data to numpy array, assuming int16 arrangement
        output = np.fromstring(raw_bytes, dtype = np.int16)

        # convert from integer type to floating point, and scale to [-1, 1]
        output = output.astype(np.float32)
        output *= (1 / 32768.0)

        # check for end-of-buffer condition:
        shortfall = num_frames * num_channels - len(output)
        continue_flag = shortfall == 0
        if shortfall > 0:
            output = np.append(output, np.zeros(shortfall))

        return (output, continue_flag)


# Refactor WaveFileGenerator into two classes: WaveFile and WaveGenerator
class WaveFile(object):
    def __init__(self, filepath) :
        super(WaveFile, self).__init__()

        self.wave = wave.open(filepath)
        self.num_channels, self.sampwidth, self.sr, self.end, \
           comptype, compname = self.wave.getparams()

        # for now, we will only accept 16 bit files at 44k
        assert(self.sampwidth == 2)
        assert(self.sr == 44100)

    # read an arbitrary chunk of data from the file
    def get_frames(self, start_frame, end_frame) :
        # get the raw data from wave file as a byte string. If asking for more than is available, it just
        # returns what it can
        self.wave.setpos(start_frame)
        raw_bytes = self.wave.readframes(end_frame - start_frame)

        # convert raw data to numpy array, assuming int16 arrangement
        samples = np.fromstring(raw_bytes, dtype = np.int16)

        # convert from integer type to floating point, and scale to [-1, 1]
        samples = samples.astype(np.float32)
        samples *= (1 / 32768.0)

        return samples

    def get_num_channels(self):
        return self.num_channels


# generates audio data by asking an audio-source (ie, WaveFile) for that data.
class WaveGenerator(object):
    def __init__(self, wave_source):
        super(WaveGenerator, self).__init__()
        self.source = wave_source
        self.frame = 0

    def generate(self, num_frames, num_channels) :
        assert(num_channels == self.source.get_num_channels())

        # get data based on our position and requested # of frames
        output = self.source.get_frames(self.frame, self.frame + num_frames)

        # advance current-frame
        self.frame += num_frames

        # check for end-of-buffer condition:
        shortfall = num_frames * num_channels - len(output)
        continue_flag = shortfall == 0
        if shortfall > 0:
            output = np.append(output, np.zeros(shortfall))

        # return
        return (output, continue_flag)


# We can generalize the thing that WaveFile does - it provides arbitrary wave
# data. We can define a "wave data providing interface" (called WaveSource)
# if it can support the function:
#
# get_frames(self, start_frame, end_frame)
#
# Now create WaveBuffer. Same WaveSource interface, but can take a subset of
# audio data from a wave file and holds all that data in memory.
class WaveBuffer(object):
    def __init__(self, filepath, start_frame, num_frames):
        super(WaveBuffer, self).__init__()

        # get a local copy of the audio data from WaveFile
        wr = WaveFile(filepath)
        self.data = wr.get_frames(start_frame, start_frame + num_frames)
        self.num_channels = wr.get_num_channels()

    # start and end args are in units of frames,
    # so take into account num_channels when accessing sample data
    def get_frames(self, start_frame, end_frame) :
        start_sample = start_frame * self.num_channels
        end_sample = end_frame * self.num_channels
        return self.data[start_sample : end_sample]

    def get_num_channels(self):
        return self.num_channels

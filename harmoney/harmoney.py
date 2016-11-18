import sys
sys.path.append('..')

from common.core import *
from common.audio import *
from common.writer import *
from common.mixer import *
from common.note import *
from common.gfxutil import topleft_label
from wavesrc_lec import *

# Same WaveSource interface, but is given audio data explicity.
class WaveArray(object):
    def __init__(self, np_array, num_channels):
        super(WaveArray, self).__init__()

        self.data = np_array
        self.num_channels = num_channels

    # start and end args are in units of frames,
    # so take into account num_channels when accessing sample data
    def get_frames(self, start_frame, end_frame) :
        start_sample = start_frame * self.num_channels
        end_sample = end_frame * self.num_channels
        return self.data[start_sample : end_sample]

    def get_num_channels(self):
        return self.num_channels


# Can record live audio into a buffer (WaveArray) and then play that same audio
# data using a WaveGenerator
class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget1, self).__init__()

        self.audio = Audio(2, input_func=self.receive_audio)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)

        self.record = False
        self.input_buffers = []
        self.live_wave = None

        self.info = topleft_label()
        self.add_widget(self.info)

    def on_update(self) :
        self.audio.on_update()
        self.info.text = 'load:%.2f\n' % self.audio.get_cpu_load()
        self.info.text += 'gain:%.2f\n' % self.mixer.get_gain()

    def receive_audio(self, frames, num_channels) :
        if self.record:
            self.input_buffers.append(frames)

    def on_key_down(self, keycode, modifiers):
        # start recording
        if keycode[1] == 'r':
            print 'start recording'
            self.record = True

        # play back live buffer
        if keycode[1] == 'p':
            if self.live_wave:
                self.mixer.add(WaveGenerator(self.live_wave))

        # adjust mixer gain
        gf = lookup(keycode[1], ('up', 'down'), (1.1, 1/1.1))
        if gf:
            new_gain = self.mixer.get_gain() * gf
            self.mixer.set_gain( new_gain )

    def on_key_up(self, keycode):
        if keycode[1] == 'r':
            print 'stop recording'
            self.record = False
            self._process_input()

    def _process_input(self) :
        data = combine_buffers(self.input_buffers)
        print 'live buffer size:', len(data) / 2, 'frames'
        np.save('recording', data)

        self.live_wave = WaveArray(data, 2)
        self.input_buffers = []

# pass in which MainWidget to run as a command-line arg
run(MainWidget)

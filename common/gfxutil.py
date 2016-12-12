#####################################################################
#
# gfxutil.py
#
# Copyright (c) 2015, Eran Egozy
#
# Released under the MIT License (http://opensource.org/licenses/MIT)
#
#####################################################################


from kivy.clock import Clock as kivyClock
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Rectangle, Ellipse, Color, Fbo, ClearBuffers, ClearColor, Line, Triangle
from kivy.graphics import PushMatrix, PopMatrix, Scale, Callback, Rotate
from kivy.graphics.texture import Texture
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.core.window import Window

import numpy as np


# return a Label object configured to look good and be positioned at
# the top-left of the screen
def topleft_label() :
    l = Label(text = "text", valign='top', font_size='20sp',
              pos=(Window.width * 0.45, Window.height * 0.4),
              text_size=(Window.width, Window.height))
    return l

def topright_label():
    l = Label(text = "text", valign='top', font_size='20sp',
              pos=(Window.width * 1.25, Window.height * 0.4),
              text_size=(Window.width, Window.height))
    return l

class Pointer(InstructionGroup):
    def __init__(self, staff, ps):
        super(Pointer, self).__init__()

        self.rotate = Rotate()
        self.add(self.rotate)

        self.half_line_width = staff.line_width / 2
        self.center = staff.bottom_y

        half_steps = [0,1,2,3,4,5,6,7,8,9,10,11]
        staff_steps = [0,.5,1,1.5,2,3,3.5,4,4.5,5,5.5,6]
        self.steps = dict(zip(half_steps, staff_steps))

        self.pointer_width = 30
        self.pointer_height = 10

        self.color = Color(1,1,1,1)
        self.add(self.color)
        self.xpos = 100
        self.ypos = self.center

        self.ps = ps


        self.pointer = Triangle()
        self._set_points()
        self.add(self.pointer)

        self.ypos_anim = KFAnim((0,0))
        self.time = 0

        self.active = False

    def _set_points(self):
        x_points = [self.xpos, self.xpos, self.xpos+self.pointer_width]
        y_points = [self.ypos + self.pointer_height, self.ypos - self.pointer_height, self.ypos]
        points = [val for pair in zip(x_points, y_points) for val in pair]
        self.pointer.points = points

    def set_pitch(self, pitch):
        self.time = 0
        old_pos = self.ypos
        diff = self._get_diff(pitch)
        self.ypos = self.center + diff 
        self.ypos_anim = KFAnim((0, old_pos), (.15, self.ypos))

    def _get_diff(self, pitch):
        half_steps = (pitch - 60) % 12
        staff_diff = self.steps[half_steps]
        diff = self.half_line_width * staff_diff
        return diff

    def change_pointer_angle(self, dir):
        self.rotate.origin = (self.xpos + self.pointer_width, self.ypos)
        if dir > 0:
            self.rotate.angle = 5
        elif dir == 0:
            self.rotate.angle = 0
        else:
            self.rotate.angle = -5

    def on_update(self, dt):
        self.ypos = self.ypos_anim.eval(self.time)
        self._set_points()
        self.time += dt
        self.change_pointer_angle(0)


class TrackPointer(InstructionGroup):
    def __init__(self, nowbar_offset, floorY, ceilingY, ps):
        super(TrackPointer, self).__init__()
        self.floorY = floorY
        self.ceilingY = ceilingY

        self.add(PushMatrix())
        self.rotate = Rotate()
        self.add(self.rotate)

        self.pointer_width = 30
        self.pointer_height = 10

        self.color = Color(1,1,1,1)
        self.add(self.color)
        self.xpos = 150 - self.pointer_width
        self.ypos = np.interp(60, [50,86], [floorY, ceilingY])
        self.ps = ps
        self.ps.emitter_x = self.xpos
        self.ps.emitter_y = self.ypos
        self.ps.start()

        self.pointer = Triangle()
        self._set_points()
        self.add(self.pointer)

        self.ypos_anim = KFAnim((0,0))
        self.time = 0

        self.add(PopMatrix())

    def _set_points(self):
        x_points = [self.xpos, self.xpos, self.xpos+self.pointer_width]
        y_points = [self.ypos + self.pointer_height, self.ypos - self.pointer_height, self.ypos]
        points = [val for pair in zip(x_points, y_points) for val in pair]
        self.pointer.points = points

    def set_pitch(self, pitch):
        pitch = pitch + 24
        # print pitch
        self.time = 0
        old_pos = self.ypos
        self.ypos = np.interp(pitch, [50,86], [self.floorY, self.ceilingY])
        self.ypos_anim = KFAnim((0, old_pos), (.15, self.ypos))

    def change_pointer_angle(self, dir):
        self.rotate.origin = (self.xpos + self.pointer_width, self.ypos)
        if dir > 0:
            self.rotate.angle = 3
        elif dir == 0:
            self.rotate.angle = 0
        else:
            self.rotate.angle = -3

    def on_update(self, dt):
        self.ypos = self.ypos_anim.eval(self.time)
        self.ps.emitter_y = 150 - self.pointer_width
        self.ps.emitter_y = self.ypos
        self._set_points()
        self.time += dt


class CatPointer(InstructionGroup):
    def __init__(self, nowbar_offset, floorY, ceilingY, ps):
        super(CatPointer, self).__init__()

        self.floorY = floorY
        self.ceilingY = ceilingY

        self.add(PushMatrix())

        # rotation and animation
        self.rotate = Rotate()
        self.add(self.rotate)
        self.rotate_anim = KFAnim((0,0))

        self.color = Color(1,1,1,1)
        self.add(self.color)

        # add nyan cat
        self.cat_width = 60
        self.cat_height = 45
        self.xpos = nowbar_offset - self.cat_width
        self.ypos = np.interp(60, [50,86], [floorY, ceilingY])
        texture = Image(source='nyancat.png').texture
        self.nyancat = Rectangle(texture=texture, pos=(150-self.cat_width, self.ypos-self.cat_height/2.),size=(self.cat_width,self.cat_height))
        self.add(self.nyancat)

        # add particle system
        self.ps = ps
        self.ps.emitter_x = self.xpos
        self.ps.emitter_y = self.ypos
        self.ps.start()

        # cat position animation
        self.ypos_anim = KFAnim((0,0))
        self.time = 0

        self.add(PopMatrix())

    def _set_points(self):
        xpos = 150 - self.cat_width
        ypos = self.ypos - self.cat_height/2.
        self.nyancat.pos = (xpos, ypos)

    def set_pitch(self, pitch):
        pitch = pitch
        self.time = 0
        old_pos = self.ypos
        self.ypos = np.interp(pitch, [50,86], [self.floorY, self.ceilingY])
        self.ypos_anim = KFAnim((0, old_pos), (.15, self.ypos))

    def change_pointer_angle(self, note_diff):
        old_angle = self.rotate.angle
        new_angle = np.interp(note_diff, [-5,5], [-20,20])
        self.rotate_anim = KFAnim((0, old_angle), (.15, new_angle))

    def on_update(self, dt):
        self.ypos = self.ypos_anim.eval(self.time)
        self.ps.emitter_y = 150 - self.cat_width
        self.ps.emitter_y = self.ypos
        self._set_points()

        self.rotate.origin = (self.xpos+(self.cat_width/2.), self.ypos)
        self.rotate.angle = self.rotate_anim.eval(self.time)
        
        self.time += dt


# Override Ellipse class to add centered functionality.
# use cpos and csize to set/get the ellipse based on a centered registration point
# instead of a bottom-left registration point
class CEllipse(Ellipse):
    def __init__(self, **kwargs):
        super(CEllipse, self).__init__(**kwargs)
        if kwargs.has_key('cpos'):
            self.cpos = kwargs['cpos']

        if kwargs.has_key('csize'):
            self.csize = kwargs['csize']

    def get_cpos(self):
        return (self.pos[0] + self.size[0]/2, self.pos[1] + self.size[1]/2)

    def set_cpos(self, p):
        self.pos = (p[0] - self.size[0]/2 , p[1] - self.size[1]/2)

    def get_csize(self) :
        return self.size

    def set_csize(self, p) :
        cpos = self.get_cpos()
        self.size = p
        self.set_cpos(cpos)

    cpos = property(get_cpos, set_cpos)
    csize = property(get_csize, set_csize)

class ClickTangle(Rectangle):
    def __init__(self, **kwargs):
        super(ClickTangle, self).__init__(**kwargs)
        if kwargs.has_key('cpos'):
            self.cpos = kwargs['cpos']

        if kwargs.has_key('csize'):
            self.csize = kwargs['csize']

    def get_cpos(self):
        return (self.pos[0] + self.size[0]/2, self.pos[1] + self.size[1]/2)

    def set_cpos(self, p):
        self.pos = (p[0] - self.size[0]/2 , p[1] - self.size[1]/2)

    def get_csize(self) :
        return self.size

    def set_csize(self, p) :
        cpos = self.get_cpos()
        self.size = p
        self.set_cpos(cpos)

    def within_bounds(self, p):
        within_x = self.pos[0] < p[0] < self.pos[0] + self.size[0]
        within_y = self.pos[1] < p[1] < self.pos[1] + self.size[1]
        return within_x and within_y

    cpos = property(get_cpos, set_cpos)
    csize = property(get_csize, set_csize)



# KeyFrame Animation class
# initialize with an argument list where each arg is a keyframe.
# one keyframe = (t, k1, k2, ...), where t is the time of the keyframe and
# k1, k2, ..., kN are the values
class KFAnim(object):
    def __init__(self, *kwargs):
        super(KFAnim, self).__init__()
        frames = zip(*kwargs)
        self.time = frames[0]
        self.frames = frames[1:]

    def eval(self, t):
        if len(self.frames) == 1:
            return np.interp(t, self.time, self.frames[0])
        else:
            return [np.interp(t, self.time, y) for y in self.frames]

    # return true if given time is within keyframe range. Otherwise, false.
    def is_active(self, t) :
        return t < self.time[-1]


# AnimGroup is a simple manager of objects that get drawn, updated with
# time, and removed when they are done
class AnimGroup(InstructionGroup) :
    def __init__(self):
        super(AnimGroup, self).__init__()
        self.objects = []

    # add an object. The object must be an InstructionGroup (ie, can be added to canvas) and
    # it must have an on_update(self, dt) method that returns True to keep going or False to end
    def add(self, obj):
        super(AnimGroup, self).add(obj)
        self.objects.append(obj)

    def on_update(self):
        dt = kivyClock.frametime
        kill_list = [o for o in self.objects if o.on_update(dt) == False]

        for o in kill_list:
            self.objects.remove(o)
            self.remove(o)

    def size(self):
        return len(self.objects)


# A graphics object for displaying a point moving in a pre-defined 3D space
# the 3D point must be in the range [0,1] for all 3 coordinates.
# depth is rendered as the size of the circle.
class Cursor3D(InstructionGroup):
    def __init__(self, area_size, area_pos, rgb, border = True):
        super(Cursor3D, self).__init__()
        self.area_size = area_size
        self.area_pos = area_pos

        if border:
            self.add(Color(1, 0, 0))
            self.add(Line(rectangle= area_pos + area_size))

        self.color = Color(*rgb)
        self.add(self.color)

        self.cursor = CEllipse(segments = 40)
        self.cursor.csize = (30,30)
        self.add(self.cursor)

    # position is a 3D point with all values from 0 to 1
    def set_pos(self, pos):
        min_sz = self.area_size[0] * 0.03
        max_sz = self.area_size[0] * 0.12
        radius = min_sz + pos[2] * (max_sz - min_sz)
        self.cursor.csize = (radius*2, radius*2)
        self.cursor.cpos = pos[0:2] * self.area_size + self.area_pos

    def set_color(self, rgb):
        self.color.rgb = rgb

    def get_screen_xy(self) :
        return self.cursor.cpos

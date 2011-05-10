#!/usr/bin/env python
"""
ClutterScope - Clutter-based software digitial storage oscilloscope
Copyright (C) 2011  Leo Singer
"""
__author__ = "Leo Singer <leo.singer@ligo.org>"


# TODO: Add fade-in effect for graticule
# TODO: Add labels for traces showing name, color, scale, etc.
# TODO: Dragging to change trace offset should snap to horizontal or vertical
# TODO: Add data API
# TODO: Add triggering


import math
import sys
import numpy
import gobject
from gi.repository import Clutter, Cogl


# Initialize Clutter
Clutter.init(sys.argv)


# Disable font mipmapping (see <http://bugzilla.clutter-project.org/show_bug.cgi?id=2584>)
Clutter.set_font_flags(0)


class ClutterScope(Clutter.Group):
	"""A Clutter-powered digital storage oscilloscope."""
	__gtype_name__ = 'ClutterScope'

	SCROLL_TIMEOUT = 250

	def __init__(self):
		super(ClutterScope, self).__init__()
		self.graticule = Graticule()
		self.add_actor(self.graticule)
		#self.set_reactive(True)

		self.traces = []

		layout = Clutter.BoxLayout()
		layout.set_vertical(False)
		layout.set_use_animations(True)
		layout.set_easing_duration(100)
		layout.set_spacing(4)
		label_box = Clutter.Box()
		label_box.set_layout_manager(layout)
		self.add_actor(label_box)
		label_box.set_position(0, 0)
		constraint = Clutter.BindConstraint()
		constraint.set_coordinate(Clutter.BindCoordinate.WIDTH)
		label_box.add_constraint(constraint)

		# Add some traces (just for looks)
		tr = Trace()
		tr.set_position(0, -50)
		self.graticule.add_actor(tr)
		self.traces += [tr]
		label_box.add_actor(TraceLabel(tr))
		tr.set_name('H1:DMT-STRAIN')

		tr = Trace()
		tr.set_color(color_from_string('magenta'))
		self.graticule.add_actor(tr)
		self.traces += [tr]
		label_box.add_actor(TraceLabel(tr))
		tr.set_name('L1:DMT-STRAIN')

		tr = Trace()
		tr.set_color(color_from_string('yellow'))
		tr.set_position(0, 50)
		self.graticule.add_actor(tr)
		self.traces += [tr]
		label_box.add_actor(TraceLabel(tr))
		tr.set_name('A1:DMT-STRAIN')

		# State for event signal handlers
		self.selected_trace = self.traces[0]
		self.__last_scroll_time = 0
		self.__drag_origin = None

	def do_scroll_event(self, event):
		time = event.time
		if time - self.__last_scroll_time > self.SCROLL_TIMEOUT:
			direction = event.direction
			if direction == Clutter.ScrollDirection.UP:
				self.selected_trace.set_scale_level_y(self.selected_trace.get_scale_level_y() + 1)
			elif direction == Clutter.ScrollDirection.DOWN:
				self.selected_trace.set_scale_level_y(self.selected_trace.get_scale_level_y() - 1)
			elif direction == Clutter.ScrollDirection.LEFT:
				scale_level = self.selected_trace.get_scale_level_x() + 1
				for trace in self.traces:
					trace.set_scale_level_x(scale_level)
			elif direction == Clutter.ScrollDirection.RIGHT:
				scale_level = self.selected_trace.get_scale_level_x() - 1
				for trace in self.traces:
					trace.set_scale_level_x(scale_level)
			self.__last_scroll_time = time

	def do_motion_event(self, event):
		if self.__drag_origin:
			actor_origin, event_origin = self.__drag_origin
			self.selected_trace.set_position(actor_origin[0] + event.x - event_origin[0], actor_origin[1] + event.y - event_origin[1])

	def do_button_press_event(self, event):
		if event.button == 1:
			self.__drag_origin = (self.selected_trace.get_position(), (event.x, event.y))

	def do_button_release_event(self, event):
		if event.button == 1:
			self.__drag_origin = None


def hline(y, x1, x2):
	"""Draw a horizontal line from (x1, y) to (x2, y)."""
	Cogl.path_line(x1, y, x2, y)


def vline(x, y1, y2):
	"""Draw a vertical line from (x, y1) to (x, y2)."""
	Cogl.path_line(x, y1, x, y2)


def color_from_string(str):
	"""Return a new instance of Clutter.Color initialized with a string."""
	color = Clutter.Color()
	if not color.from_string(str):
		raise RuntimeError
	return color


def cogl_color_from_clutter_color(c):
	"""Return a Cogl.Color that is equivalent to a Clutter.Color."""
	cogl_color = Cogl.Color()
	cogl_color.init_from_4ub(c.red, c.green, c.blue, c.alpha)
	return cogl_color


class animate(object):
	def __init__(self):
		self.__objs = {}

	def __destroy(self, actor, user_data):
		del self.__objs[actor]

	def __call__(self, actor, mode, duration, **kwargs):
		try:
			animations = self.__objs[actor]
		except KeyError:
			animations = {}
			self.__objs[actor] = animations
			actor.connect('destroy', self.__destroy)

		for key, value in kwargs.iteritems():
			key = key.replace('_', '-')

			try:
				animation = animations[key]
				animation.unbind_property(key)
			except KeyError:
				animation = Clutter.Animation()
				animation.set_object(actor)
				animations[key] = animation
			animation.set_duration(duration)
			animation.bind(key, value)
			animation.get_timeline().start()
animate = animate()


def ignore_last_arg(call):
	return lambda *args: call(*args[:-1])


class GroupNoLayout(Clutter.Group):
	"""A Group that ignores its layout manager, so its size is not affected by
	the allocations of its children."""

	__gtype_name__ = 'GroupNoLayout'

	def __init__(self):
		super(GroupNoLayout, self).__init__()

	def do_get_preferred_width(self, width):
		return (0., width)

	def do_get_preferred_height(self, height):
		return (0., height)


class Graticule(GroupNoLayout):
	"""Actor that provides grid and axes for a ClutterScope.
	This actor paints into an area that extends from half its width above its
	top to half its width above its bottom, so that it is possible to conveniently
	parent objects to it and have their coordinates referenced from (0, 0) refer
	to the center of the stage."""
	__gtype_name__ = 'Graticule'

	"""Pixels between major gridlines"""
	MAJOR_PIXELS = 60

	"""Background color"""
	BACKGROUND_COLOR = color_from_string('#282828')

	"""Gridline color"""
	GRIDLINE_COLOR = color_from_string('#3c3c3c')

	def __init__(self):
		super(Graticule, self).__init__()
		self.__constraints = []

		constraint = Clutter.AlignConstraint()
		constraint.set_factor(0.5)
		constraint.set_align_axis(Clutter.AlignAxis.X_AXIS)
		self.__constraints += [constraint]

		constraint = Clutter.AlignConstraint()
		constraint.set_align_axis(Clutter.AlignAxis.Y_AXIS)
		constraint.set_factor(0.5)
		self.__constraints += [constraint]

		constraint = Clutter.BindConstraint()
		constraint.set_coordinate(Clutter.BindCoordinate.SIZE)
		self.__constraints += [constraint]

		for constraint in self.__constraints:
			self.add_constraint(constraint)

		self.connect('paint', self.paint)

	@staticmethod
	def paint(self):
		"""paint signal handler."""
		w, h = self.get_size()
		half_w = 0.5 * w
		half_h = 0.5 * h
		half_major = self.MAJOR_PIXELS / 2
		tenth_major = self.MAJOR_PIXELS / 10

		# Fill background.
		Cogl.set_source_color(cogl_color_from_clutter_color(self.BACKGROUND_COLOR))
		Cogl.rectangle(-half_w, -half_h, half_w, half_h)

		# Create paths for vertical gridlines.
		x0 = int((-half_w // self.MAJOR_PIXELS) * self.MAJOR_PIXELS)
		for x in xrange(x0, int(math.ceil(half_w)), self.MAJOR_PIXELS):
			halfway = x + half_major
			vline(x, -half_h, half_h)
			vline(halfway, -8, 0)
			for xx in xrange(x + tenth_major, halfway, tenth_major):
				vline(xx, -4, 0)
			for xx in xrange(halfway + tenth_major, x + self.MAJOR_PIXELS, tenth_major):
				vline(xx, -4, 0)

		# Create paths for horizontal gridlines.
		y0 = int((-half_h // self.MAJOR_PIXELS) * self.MAJOR_PIXELS)
		for y in xrange(y0, int(math.ceil(half_h)), self.MAJOR_PIXELS):
			halfway = y + half_major
			hline(y, -half_w, half_w)
			hline(halfway, 0, 8)
			for yy in xrange(y + tenth_major, halfway, tenth_major):
				hline(yy, 0, 4)
			for yy in xrange(halfway + tenth_major, y + self.MAJOR_PIXELS, tenth_major):
				hline(yy, 0, 4)

		# Stroke gridlines.
		Cogl.set_source_color(cogl_color_from_clutter_color(self.GRIDLINE_COLOR))
		Cogl.path_stroke()

	def do_parent_set(self, old_parent):
		parent = self.get_parent()
		for constraint in self.__constraints:
			constraint.set_source(parent)


class Trace(Clutter.Actor):
	__gtype_name__ = 'Trace'

	__gproperties__ = {
		'color': (
			Clutter.Color,
			'color',
			'Trace stroke color',
			gobject.PARAM_READWRITE
		),
		'scale-level-x': (
			gobject.TYPE_INT,
			'scale-level-x',
			'Scale level, x-axis',
			gobject.G_MININT, gobject.G_MAXINT, 0,
			gobject.PARAM_READWRITE
		),
		'scale-level-y': (
			gobject.TYPE_INT,
			'scale-level-y',
			'Scale level, y-axis',
			gobject.G_MININT, gobject.G_MAXINT, 0,
			gobject.PARAM_READWRITE
		)
	}

	def __init__(self):
		super(Trace, self).__init__()
		#self.set_size(0, 0)
		#self.set_fixed_position_set(True)
		self.set_anchor_point_from_gravity(Clutter.Gravity.CENTER)
		self.color = color_from_string('cyan')
		self.scale_level_x = 0
		self.scale_level_y = 0

	def do_set_property(self, prop, val):
		if prop.name == 'color':
			old_color = self.color
			self.color = val
			if old_color != self.color:
				self.queue_redraw()
		elif prop.name == 'scale-level-x':
			self.scale_level_x = val
			a, b = divmod(val, 2)
			scale = 10 ** a
			if b:
				scale *= 2
			animate(self, Clutter.AnimationMode.LINEAR, 250, scale_x = float(scale))
		elif prop.name == 'scale-level-y':
			self.scale_level_y = val
			a, b = divmod(val, 2)
			scale = 10 ** a
			if b:
				scale *= 2
			animate(self, Clutter.AnimationMode.LINEAR, 250, scale_y = float(scale))

	def do_get_property(self, prop):
		if prop.name == 'color':
			return self.color
		elif prop.name == 'scale-level-x':
			return self.scale_level_x
		elif prop.name == 'scale-level-y':
			return self.scale_level_y

	def set_color(self, val):
		self.set_property('color', val)

	def get_color(self):
		return self.get_property()

	def set_scale_level_x(self, val):
		self.set_property('scale-level-x', val)

	def get_scale_level_x(self):
		return self.get_property('scale-level-x')

	def set_scale_level_y(self, val):
		self.set_property('scale-level-y', val)

	def get_scale_level_y(self):
		return self.get_property('scale-level-y')

	def do_paint(self):
		x = numpy.arange(-400, 400)
		y = 20 * numpy.sin(x * 0.1)

		# Plot trace, setting down lines wherever both x and y are finite
		# (neither NaN, nor infinity, nor minus infinity)
		pendown = False
		for x, y in zip(x, y):
			if numpy.isfinite(x) and numpy.isfinite(y):
				#x -= self.get_x()
				#y -= self.get_y()
				if pendown:
					Cogl.path_line_to(x, -y)
				else:
					Cogl.path_move_to(x, -y)
					pendown = True
			else:
				pendown = False
		Cogl.set_source_color(cogl_color_from_clutter_color(self.color))
		Cogl.path_stroke()


class TraceLabel(Clutter.Group):
	"""Label for a trace showing its name, color, and scale."""
	__gtype_name__ = 'TraceLabel'

	def __init__(self, trace):
		super(TraceLabel, self).__init__()
		self.trace = trace
		self.set_size(144, 48)
		self.name_label = Clutter.Text()
		self.name_label.set_color(color_from_string('black'))
		self.name_label.set_text('foo bar')
		self.add_actor(self.name_label)
		self.name_label.set_position(6, 6)
		self.name_label.set_size(*self.get_size())
		self.connect('paint', self.paint)
		self.trace.connect_after('notify::color', self.color_changed)
		self.trace.connect_after('notify::name', self.name_changed)

	def color_changed(self, param, user_data):
		self.queue_redraw()

	def name_changed(self, param, user_data):
		self.name_label.set_text(self.trace.get_name())

	@staticmethod
	def paint(self):
		"""paint signal handler."""
		w, h = self.get_size()
		color = self.trace.color
		dark_color = color.darken()

		Cogl.set_source_color(cogl_color_from_clutter_color(dark_color))
		Cogl.path_round_rectangle(0, 0, w, h, 5, 10)
		Cogl.path_fill()

		Cogl.set_source_color(cogl_color_from_clutter_color(color))
		Cogl.path_round_rectangle(3, 3, w - 3, h - 3, 3, 10)
		Cogl.path_fill()


stage = Clutter.Stage.get_default()
stage.set_size(576, 576)
stage.connect('destroy', ignore_last_arg(Clutter.main_quit))
stage.set_user_resizable(True)

scope = ClutterScope()
stage.add_actor(scope)
scope.set_reactive(True)
constraint = Clutter.BindConstraint()
constraint.set_coordinate(Clutter.BindCoordinate.SIZE | Clutter.BindCoordinate.POSITION)
constraint.set_source(stage)
scope.add_constraint(constraint)

stage.show_all()
Clutter.main()

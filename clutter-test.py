#!/usr/bin/env python

import math
import numpy
import clutter
import gobject
from clutter import cogl

stage = clutter.Stage()


class ClutterScope(clutter.Actor):
	"""A Clutter-powered digital storage oscilloscope."""
	__gtype_name__ = 'ClutterScope'


def hline(y, x1, x2):
	"""Draw a horizontal line from (x1, y) to (x2, y)."""
	cogl.path_line(x1, y, x2, y)


def vline(x, y1, y2):
	"""Draw a vertical line from (x, y1) to (x, y2)."""
	cogl.path_line(x, y1, x, y2)


class Graticule(clutter.Group):
	"""Actor that provides grid and axes for a ClutterScope.
	This actor paints into an area that extends from half its width above its
	top to half its width above its bottom, so that it is possible to conveniently
	parent objects to it and have their coordinates referenced from (0, 0) refer
	to the center of the stage."""
	__gtype_name__ = 'Graticule'

	"""Pixels between major gridlines"""
	MAJOR_PIXELS = 60

	"""Background color"""
	BACKGROUND_COLOR = clutter.Color(40, 40, 40, 255)

	"""Gridline color"""
	GRIDLINE_COLOR = clutter.Color(60, 60, 60, 255)

	def __init__(self):
		super(Graticule, self).__init__()
		self.__bind_constraint = None
		# FIXME: replace allocation-changed handler with align constraints
		self.__allocation_changed_handler = None

	def do_paint(self):
		"""paint signal handler."""
		w = self.get_width()
		h = self.get_height()
		half_w = 0.5 * w
		half_h = 0.5 * h
		half_major = self.MAJOR_PIXELS / 2
		tenth_major = self.MAJOR_PIXELS / 10

		# Fill background.
		cogl.set_source_color(self.BACKGROUND_COLOR)
		cogl.rectangle(-half_w, -half_h, half_w, half_h)

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
		cogl.set_source_color(self.GRIDLINE_COLOR)
		cogl.path_stroke()

		# Chain up to parent.
		clutter.Group.do_paint(self)

	def parent_allocation_changed(self, parent, box, flags):
		"""parent's allocation-changed signal handler."""
		parent_width = box.get_width()
		parent_height = box.get_height()
		self.set_position(0.5 * parent_width, 0.5 * parent_height)

	def do_parent_set(self, old_parent):
		"""parent-set signal handler."""
		parent = self.get_parent()
		if self.__bind_constraint:
			self.remove_constraint(self.__bind_constraint)
		if parent:
			self.__bind_constraint = clutter.BindConstraint(parent, clutter.BIND_SIZE, 0.)
			self.add_constraint(self.__bind_constraint)
		else:
			self.__bind_constraint = None
		if self.__allocation_changed_handler:
			if old_parent and self.__allocation_changed_handler:
				old_parent.disconnect(self.__allocation_changed_handler)
		if parent:
			self.__allocation_changed_handler = parent.connect_after('allocation-changed', self.parent_allocation_changed)
		else:
			self.__allocation_changed_handler = None
		if parent:
			self.set_position(0.5 * parent.get_width(), 0.5 * parent.get_height())



class Trace(clutter.Actor):
	__gtype_name__ = 'Trace'

	__gproperties__ = {
		'color': (
			clutter.Color,
			'color',
			'Trace stroke color',
			gobject.PARAM_READWRITE
		)
	}

	def __init__(self):
		super(Trace, self).__init__()
		self.set_size(0, 0)
		self.set_anchor_point_from_gravity(clutter.GRAVITY_CENTER)
		self.color = clutter.color_from_string('cyan')

	def do_set_property(self, prop, val):
		if prop.name == 'color':
			old_color = self.color
			self.color = val
			if old_color != self.color:
				self.queue_redraw()

	def do_get_property(self, prop):
		if prop.name == 'color':
			return self.color

	def set_color(self, color):
		self.set_property('color', color)

	def get_color(self):
		return self.get_property(color)

	def do_paint(self):
		x = numpy.arange(-400, 400)
		y = 20 * numpy.sin(x * 0.1)

		# Plot trace, setting down lines wherever both x and y are finite
		# (neither NaN, nor infinity, nor minus infinity)
		pendown = False
		for x, y in zip(x, y):
			if numpy.isfinite(x) and numpy.isfinite(y):
				if pendown:
					cogl.path_line_to(x, -y)
				else:
					cogl.path_move_to(x, -y)
					pendown = True
			else:
				pendown = False
		cogl.set_source_color(self.color)
		cogl.path_stroke()

stage.set_size(576, 576)
stage.connect('destroy', clutter.main_quit)
stage.set_user_resizable(True)

gr = Graticule()
stage.add(gr)

tr = Trace()
tr.set_position(0, -50)
gr.add(tr)

tr = Trace()
tr.set_color(clutter.color_from_string('magenta'))
gr.add(tr)

tr = Trace()
tr.set_color(clutter.color_from_string('yellow'))
tr.set_position(0, 50)
gr.add(tr)

stage.show_all()
clutter.main()

#!/usr/bin/env python

import math
import numpy
import clutter
import gobject
from clutter import cogl

stage = clutter.Stage()

bgcolor = clutter.Color(40, 40, 40, 255)
grcolor = clutter.Color(60, 60, 60, 255)

class Graticule(clutter.Actor):
	"""Draw grid."""
	__gtype_name__ = 'Graticule'

	def do_paint(self):
		half_w = 0.5 * self.get_width()
		half_h = 0.5 * self.get_height()
		half = long(math.ceil(max(half_w, half_h)))
		cogl.set_source_color(grcolor)
		cogl.push_matrix()
		cogl.translate(half_w, half_h, 0)
		for j in range(2):
			for i in range(2):
				for x in range(0, half, 60):
					cogl.path_line(x, -half, x, half)
				for x in range(0, half, 6):
					cogl.path_line(x, 0, x, -4)
				for x in range(0, half, 30):
					cogl.path_line(x, 0, x, -8)
				cogl.path_stroke()
				cogl.scale(-1, 1, 1)
			cogl.rotate(90, 0, 0, 1)
		cogl.pop_matrix()

class Trace(clutter.Rectangle):
	__gtype_name__ = 'Trace'

	def __init__(self):
		super(Trace, self).__init__()
		self.set_anchor_point(0.5 * self.get_width(), 0.5 * self.get_height())
		#self.set_anchor_point_from_gravity(clutter.GRAVITY_CENTER)
		#self.set_property('scale-gravity', 'center')
		self.color = clutter.color_from_string('cyan')

		drag = clutter.DragAction()
		drag.set_drag_axis(clutter.DRAG_X_AXIS)
		drag.set_drag_threshold(24, gobject.G_MAXUINT)
		self.add_action(drag)

		drag = clutter.DragAction()
		drag.set_drag_axis(clutter.DRAG_Y_AXIS)
		drag.set_drag_threshold(gobject.G_MAXUINT, 24)

		self.last_time = 0
		self.add_action(drag)
		self.connect_after('scroll-event', self.scroll)
		self.set_reactive(True)

	@staticmethod
	def scroll(self, event):
		if event.time - self.last_time > 100:
			direction = event.direction
			x, y = self.get_scale()
			if direction == clutter.SCROLL_UP:
				self.set_scale(x, 2 * y)
			elif direction == clutter.SCROLL_DOWN:
				if y > 1. / 4:
					self.set_scale(x, 0.5 * y)
			elif direction == clutter.SCROLL_LEFT:
				self.set_scale(2 * x, y)
			elif direction == clutter.SCROLL_RIGHT:
				if x > 1. / 4:
					self.set_scale(0.5 * x, y)
			self.last_time = event.time

	def do_paint(self):
		x = numpy.arange(800)
		#y = 20*numpy.random.randn(len(x))
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
stage.set_color(bgcolor)

gr = Graticule()
tr = Trace()
tr.set_size(*stage.get_size())
tr.set_position(0, 576/2)
stage.add(gr)
stage.add(tr)
tr.set_reactive(True)
gr.add_constraint(clutter.BindConstraint(stage, clutter.BIND_SIZE | clutter.BIND_POSITION, 0))
#tr.add_constraint(clutter.BindConstraint(stage, clutter.BIND_SIZE, 0))

stage.connect('destroy', clutter.main_quit)
stage.set_user_resizable(True)
stage.show_all()
clutter.main()

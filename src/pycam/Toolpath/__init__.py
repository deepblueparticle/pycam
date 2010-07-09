# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2010 Lars Kruse <devel@sumpfralle.de>

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

__all__ = ["ToolPathList", "ToolPath", "Generator"]

from pycam.Geometry.Point import Point
import pycam.Gui.Settings
import random
import os


class ToolPathList(list):

    def add_toolpath(self, toolpath, name, toolpath_settings):
        self.append(ToolPath(toolpath, name, toolpath_settings))


class ToolPath:

    def __init__(self, toolpath, name, toolpath_settings):
        self.toolpath = toolpath
        self.name = name
        self.toolpath_settings = toolpath_settings
        self.visible = True
        self.color = None
        # generate random color
        self.set_color()

    def get_path(self):
        return self.toolpath

    def get_start_position(self):
        safety_height = self.toolpath_settings.get_process_settings()["safety_height"]
        for path in self.toolpath:
            if path.points:
                p = path.points[0]
                return Point(p.x, p.y, safety_height)
        else:
            return Point(0, 0, safety_height)

    def get_bounding_box(self):
        box = self.toolpath_settings.get_bounds()
        return (box["minx"], box["maxx"], box["miny"], box["maxy"], box["minz"],
                box["maxz"])

    def get_tool_settings(self):
        return self.toolpath_settings.get_tool_settings()

    def get_toolpath_settings(self):
        return self.toolpath_settings

    def get_meta_data(self):
        meta = self.toolpath_settings.get_string()
        start_marker = self.toolpath_settings.META_MARKER_START
        end_marker = self.toolpath_settings.META_MARKER_END
        return os.linesep.join((start_marker, meta, end_marker))

    def set_color(self, color=None):
        if color is None:
            self.color = (random.random(), random.random(), random.random())
        else:
            self.color = color

    def get_machine_time(self, start_position=None):
        """ calculate an estimation of the time required for processing the
        toolpath with the machine

        @value start_position: (optional) the position of the tool before the
                start
        @type start_position: pycam.Geometry.Point.Point
        @rtype: float
        @returns: the machine time used for processing the toolpath in minutes
        """
        if start_position is None:
            start_position = Point(0, 0, 0)
        feedrate = self.toolpath_settings.get_tool_settings()["feedrate"]
        def move(new_pos):
            move.result_time += new_pos.sub(move.current_position).norm() / feedrate
            move.current_position = new_pos
        move.current_position = start_position
        move.result_time = 0
        # move to safey height at the starting position
        safety_height = self.toolpath_settings.get_process_settings()["safety_height"]
        move(Point(start_position.x, start_position.y, safety_height))
        for path in self.get_path():
            # go to safety height (horizontally from the previous x/y location)
            if len(path.points) > 0:
                move(Point(path.points[0].x, path.points[0].y, safety_height))
            # go through all points of the path
            for point in path.points:
                move(point)
            # go to safety height (vertically up from the current x/y location)
            if len(path.points) > 0:
                move(Point(path.points[-1].x, path.points[-1].y, safety_height))
        return move.result_time


class Bounds:

    TYPE_RELATIVE_MARGIN = 0
    TYPE_FIXED_MARGIN = 1
    TYPE_CUSTOM = 2

    def __init__(self, bounds_type=None, bounds_low=None, bounds_high=None,
            ref_low=None, ref_high=None):
        """ create a new Bounds instance

        @value bounds_type: any of TYPE_RELATIVE_MARGIN | TYPE_FIXED_MARGIN | TYPE_CUSTOM
        @type bounds_type: int
        @value bounds_low: the lower margin of the boundary compared to the
            reference object (for TYPE_RELATIVE_MARGIN | TYPE_FIXED_MARGIN) or
            the specific boundary values (for TYPE_CUSTOM). Only the lower
            values of the three axes (x, y and z) are given.
        @type bounds_low: (tuple|list) of float
        @value bounds_high: see 'bounds_low'
        @type bounds_high: (tuple|list) of float
        @value ref_low: a reference object described by a tuple (or list) of
            three item. These three values describe only the lower boundary of
            this object (for the x, y and z axes). Each item must be callable
            or a float value. In case of a callable reference, the up-to-date
            result of this callable is used whenever a value is calculated.
            Thus there is no need to trigger a boundary update manually when
            using callables as references. A mixed tuple of float values and
            callables is allowed.
            This argument is ignored for the boundary type "TYPE_CUSTOM".
        @type ref_low: (tuple|list) of (float|callable)
        @value ref_high: see 'ref_low'
        @type ref_high: (tuple|list) of (float|callable)
        """
        self.name = "No name"
        if ref_low is None or ref_high is None:
            # only the "custom" bounds model does not depend on a reference
            bounds_type = self.TYPE_CUSTOM
        # set type
        if bounds_type is None:
            self.set_type(self.TYPE_RELATIVE_MARGIN)
        else:
            self.set_type(bounds_type)
        # store all reference values as callables (to simplify later usage)
        self.ref_low = []
        self.ref_high = []
        for in_values, out in ((ref_low, self.ref_low), (ref_high, self.ref_high)):
            if not in_values is None:
                for index in range(3):
                    if callable(in_values[index]):
                        out.append(in_values[index])
                    else:
                        # Create new variables within the scope of the lambda
                        # function.
                        # The lambda function just returns the float value.
                        out.append(lambda in_values=in_values, index=index:
                                in_values[index])
            else:
                out.extend([0, 0, 0])
        # store the bounds values
        if bounds_low is None:
            bounds_low = [0, 0, 0]
        if bounds_high is None:
            bounds_high = [0, 0, 0]
        self.set_bounds(bounds_low, bounds_high)

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def get_type(self):
        return self.bounds_type

    def set_type(self, bounds_type):
        # complain if an unknown bounds_type value was given
        if not bounds_type in (Bounds.TYPE_RELATIVE_MARGIN,
                Bounds.TYPE_FIXED_MARGIN, Bounds.TYPE_CUSTOM):
            raise ValueError, "failed to create an instance of " \
                    + "pycam.Toolpath.Bounds due to an invalid value of " \
                    + "'bounds_type': %s" % repr(bounds_type)
        else:
            self.bounds_type = bounds_type

    def get_bounds(self):
        return self.bounds_low[:], self.bounds_high[:]

    def set_bounds(self, low=None, high=None):
        if not low is None:
            if len(low) != 3:
                raise ValueError, "lower bounds should be supplied as a " \
                        + "tuple/list of 3 items - but %d were given" % len(low)
            else:
                self.bounds_low = list(low[:])
        if not high is None:
            if len(high) != 3:
                raise ValueError, "upper bounds should be supplied as a " \
                        + "tuple/list of 3 items - but %d were given" % len(high)
            else:
                self.bounds_high = list(high[:])

    def get_absolute_limits(self):
        """ calculate the current absolute limits of the Bounds instance

        @returns: a tuple of two lists containg the low and high limits
        @rvalue: tuple(list)
        """
        # copy the original dict
        low = [None] * 3
        high = [None] * 3
        # calculate the absolute limits
        if self.bounds_type == self.TYPE_RELATIVE_MARGIN:
            for index in range(3):
                dim_width = self.ref_high[index]() - self.ref_low[index]()
                low[index] = self.ref_low[index]() \
                        - self.bounds_low[index] * dim_width
                high[index] = self.ref_high[index]() \
                        + self.bounds_high[index] * dim_width
        elif self.bounds_type == self.TYPE_FIXED_MARGIN:
            for index in range(3):
                low[index] = self.ref_low[index]() - self.bounds_low[index]
                high[index] = self.ref_high[index]() + self.bounds_high[index]
        elif self.bounds_type == self.TYPE_CUSTOM:
            for index in range(3):
                low[index] = self.bounds_low[index]
                high[index] = self.bounds_high[index]
        else:
            # this should not happen
            raise NotImplementedError, "the function 'get_absolute_limits' is" \
                    + " currently not implemented for the bounds_type " \
                    + "'%s'" % str(self.bounds_type)
        return low, high

    def adjust_bounds_to_absolute_limits(self, limits_low, limits_high):
        """ change the current bounds settings according to some absolute values

        This does not change the type of this bounds instance (e.g. relative).
        @value limits_low: a tuple describing the new lower absolute boundary
        @type limits_low: (tuple|list) of float
        @value limits_high: a tuple describing the new lower absolute boundary
        @type limits_high: (tuple|list) of float
        """
        # calculate the new settings
        if self.bounds_type == self.TYPE_RELATIVE_MARGIN:
            for index in range(3):
                self.bounds_low[index] = \
                        (self.ref_low[index]() - limits_low[index]) \
                        / (self.ref_high[index]() - self.ref_low[index]())
                self.bounds_high[index] = \
                        (limits_high[index] - self.ref_high[index]()) \
                        / (self.ref_high[index]() - self.ref_low[index]())
        elif self.bounds_type == self.TYPE_FIXED_MARGIN:
            for index in range(3):
                self.bounds_low[index] = self.ref_low[index]() - limits_low[index]
                self.bounds_high[index] = limits_high[index] - self.ref_high[index]()
        elif self.bounds_type == self.TYPE_CUSTOM:
            for index in range(3):
                self.bounds_low[index] = limits_low[index]
                self.bounds_high[index] = limits_high[index]
        else:
            # this should not happen
            raise NotImplementedError, "the function " \
                    + "'adjust_bounds_to_absolute_limits' is currently not " \
                    + "implemented for the bounds_type '%s'" \
                    % str(self.bounds_type)


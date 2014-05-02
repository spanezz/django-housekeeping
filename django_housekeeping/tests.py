# coding: utf8
#
# Copyright (C) 2014  Enrico Zini <enrico@debian.org>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3.0 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from . import Task, Housekeeping
from . import toposort
import unittest

class TestHousekeeping(unittest.TestCase):
    def test_run(self):
        class TestTask(Task):
            run_count = 0
            def run(self):
                TestTask.run_count += 1

        h = Housekeeping()
        h.register_task(TestTask)
        h.run()
        self.assertEquals(TestTask.run_count, 1)

class TestToposort(unittest.TestCase):
    def test_simple(self):
        self.assertEquals(toposort.sort({ 0 : [2], 1: [2], 2: [3], 3: [] }), [1, 0, 2, 3])
        self.assertRaises(ValueError, toposort.sort, { 0: [1], 1: [2], 2: [3], 3: [1] })
        self.assertRaises(ValueError, toposort.sort, { 0: [1], 1: [0], 2: [3], 3: [2] })

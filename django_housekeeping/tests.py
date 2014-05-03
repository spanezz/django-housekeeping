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
            def run_main(self, stage):
                TestTask.run_count += 1

        h = Housekeeping()
        h.register_task(TestTask)
        h.init()
        h.run()
        self.assertEquals(TestTask.run_count, 1)

class TestToposort(unittest.TestCase):
    def test_simple(self):
        self.assertEquals(toposort.sort({ 0 : [2], 1: [2], 2: [3], 3: [] }), [1, 0, 2, 3])
        self.assertRaises(ValueError, toposort.sort, { 0: [1], 1: [2], 2: [3], 3: [1] })
        self.assertRaises(ValueError, toposort.sort, { 0: [1], 1: [0], 2: [3], 3: [2] })

    def test_real(self):
        class Backup1(Task):
            STAGES = [ "backup", "main" ]
            def run_backup(self): pass

        class Backup2(Task):
            DEPENDS = [Backup1]
            STAGES = [ "backup", "main" ]
            def run_backup(self): pass

        class LoadData(Task):
            NAME = "data"
            STAGES = [ "main", "stats" ]
            def run_main(self): pass
            def run_stats(self): pass

        class Consistency(Task):
            DEPENDS = [LoadData]
            STAGES = [ "main", "stats" ]
            def run_main(self): pass
            def run_stats(self): pass

        h = Housekeeping()
        h.register_task(Backup2)
        h.register_task(Consistency)
        h.register_task(Backup1)
        h.register_task(LoadData)
        h.init()
        order = [(stage.name, task.IDENTIFIER) for stage, task in h.get_schedule()]
        self.assertEquals(order, [
            ('backup', 'django_housekeeping.tests.Backup1'),
            ('backup', 'django_housekeeping.tests.Backup2'),
            ('main', 'django_housekeeping.tests.LoadData'),
            ('main', 'django_housekeeping.tests.Consistency'),
            ('stats', 'django_housekeeping.tests.LoadData'),
            ('stats', 'django_housekeeping.tests.Consistency'),
        ])

    def test_stage_without_tasks(self):
        class Backup(Task):
            STAGES = [ "backup", "main" ]
            def run_backup(self): pass

        h = Housekeeping()
        h.register_task(Backup)
        h.init()
        order = [(stage.name, task.IDENTIFIER) for stage, task in h.get_schedule()]
        self.assertEquals(order, [
            (u'backup', u'django_housekeeping.tests.Backup'),
        ])

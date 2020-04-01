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
from __future__ import annotations
from . import Task, Housekeeping
from . import toposort
import unittest
import os.path


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
        self.assertEqual(TestTask.run_count, 1)


class TestToposort(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(toposort.sort({0: [2], 1: [2], 2: [3], 3: []}), [1, 0, 2, 3])
        with self.assertRaises(ValueError):
            toposort.sort({0: [1], 1: [2], 2: [3], 3: [1]})
        with self.assertRaises(ValueError):
            toposort.sort({0: [1], 1: [0], 2: [3], 3: [2]})

    def test_real(self):
        class Backup1(Task):
            STAGES = ["backup", "main"]

            def run_backup(self): pass

        class Backup2(Task):
            DEPENDS = [Backup1]
            STAGES = ["backup", "main"]

            def run_backup(self): pass

        class LoadData(Task):
            NAME = "data"
            STAGES = ["main", "stats"]

            def run_main(self): pass

            def run_stats(self): pass

        class Consistency(Task):
            DEPENDS = [LoadData]
            STAGES = ["main", "stats"]

            def run_main(self): pass

            def run_stats(self): pass

        h = Housekeeping()
        h.register_task(Backup2)
        h.register_task(Consistency)
        h.register_task(Backup1)
        h.register_task(LoadData)
        h.init()
        order = [(stage.name, task.IDENTIFIER) for stage, task in h.get_schedule()]
        self.assertEqual(order, [
            ('backup', 'django_housekeeping.tests.Backup1'),
            ('backup', 'django_housekeeping.tests.Backup2'),
            ('main', 'django_housekeeping.tests.LoadData'),
            ('main', 'django_housekeeping.tests.Consistency'),
            ('stats', 'django_housekeeping.tests.LoadData'),
            ('stats', 'django_housekeeping.tests.Consistency'),
        ])

    def test_stage_without_tasks(self):
        class Backup(Task):
            STAGES = ["backup", "main"]

            def run_backup(self): pass

        h = Housekeeping()
        h.register_task(Backup)
        h.init()
        order = [(stage.name, task.IDENTIFIER) for stage, task in h.get_schedule()]
        self.assertEqual(order, [
            (u'backup', u'django_housekeeping.tests.Backup'),
        ])


class TestDependencies(unittest.TestCase):
    def test_skipstage(self):
        class Associator(Task):
            run_count = 0
            call_history = []
            NAME = "associate"
            STAGES = ["main", "stats"]

            def run_stats(self, stage):
                Associator.run_count += 1

            def __call__(self, name):
                self.call_history.append(name)

        class AssociateFoo(Task):
            DEPENDS = [Associator]

            def run_main(self, stage):
                self.hk.associate("foo")

        h = Housekeeping()
        h.register_task(Associator)
        h.register_task(AssociateFoo)
        h.init()
        h.run()

        self.assertEqual(Associator.run_count, 1)
        self.assertEqual(Associator.call_history, ["foo"])


class TestReport(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root)

    def test_report(self):
        class TestTask(Task):
            STAGES = ["main", "stats"]

            def run_main(self, stage): pass

            def run_stats(self, stage): pass

        h = Housekeeping(outdir=self.root)
        h.register_task(TestTask)
        h.init()
        h.run()

        self.assertTrue(os.path.isfile(os.path.join(h.outdir.outdir, "report/tasks.dot")))
        self.assertTrue(os.path.isfile(os.path.join(h.outdir.outdir, "report/stages.dot")))
        self.assertTrue(os.path.isfile(os.path.join(h.outdir.outdir, "report/stage-main.dot")))
        self.assertTrue(os.path.isfile(os.path.join(h.outdir.outdir, "report/stage-stats.dot")))

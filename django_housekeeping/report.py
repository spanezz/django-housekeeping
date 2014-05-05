# coding: utf8
# Pluggable housekeeping framework for Django sites
#
# Copyright (C) 2013--2014  Enrico Zini <enrico@enricozini.org>
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
import io
import os, os.path

class Report(object):
    def __init__(self, hk):
        self.hk = hk
        self.dotfiles = []
        self.root = None

    def make_dotfile(self, name):
        self.dotfiles.append(name)
        return io.open(os.path.join(self.root, name), "wt", encoding="utf8")

    def generate(self):
        if not self.hk.outdir: return
        # Main report dir
        self.root = self.hk.outdir.make_path("report")

        # .dot files with dependency graphs
        with self.make_dotfile("tasks.dot") as out:
            print("digraph TASKS {", file=out)
            print('  label="Tasks"', file=out)
            self.hk.task_schedule.make_dot(out, formatter=lambda x:x.IDENTIFIER)
            print("}", file=out)
        with self.make_dotfile("stages.dot") as out:
            print("digraph STAGES {", file=out)
            print('  label="Stages"', file=out)
            self.hk.stage_schedule.make_dot(out)
            print("}", file=out)
        for stage in self.hk.stages.itervalues():
            with self.make_dotfile("stage-{}.dot".format(stage.name)) as out:
                print("digraph {} {{".format(stage.name), file=out)
                print('  label="Stage {}"'.format(stage.name), file=out)
                stage.task_schedule.make_dot(out)
                print("}", file=out)

        # Makefile to build the HTML report
        with io.open(os.path.join(self.root, "Makefile"), "wt", encoding="utf8") as out:
            print("%.png: %.dot", file=out)
            print("\tdot -T png $< -o $@", file=out)


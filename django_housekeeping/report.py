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
import sys

import six

class Report(object):
    def __init__(self, hk):
        self.hk = hk
        self.dotfiles = []
        self.root = None

    def make_dotfile(self, name):
        self.dotfiles.append(name)
        return io.open(os.path.join(self.root, name), "wt", encoding="utf8")

    def print_title(self, title, underline_char, file=sys.stdout):
        print(title, file=file)
        print(underline_char * len(title), file=file)

    def print_depgraph_legend(self, file=sys.stdout):
        print("   +------------+---------------------------------------+", file=file)
        print("   | Arrow type | Meaning                               |", file=file)
        print("   +============+=======================================+", file=file)
        print("   | Solid      | Dependency                            |", file=file)
        print("   +------------+---------------------------------------+", file=file)
        print("   | Bold       | Dependency and chosen execution order |", file=file)
        print("   +------------+---------------------------------------+", file=file)
        print("   | Dashed     | Chosen execution order                |", file=file)
        print("   +------------+---------------------------------------+", file=file)

    def generate(self):
        if not self.hk.outdir: return
        # Main report dir
        self.root = self.hk.outdir.path("report")

        self.generate_dotfiles()

        with io.open(os.path.join(self.root, "report.rst"), "wt", encoding="utf8") as out:
            self.generate_report(file=out)

        # Makefile to build the HTML report
        with io.open(os.path.join(self.root, "Makefile"), "wt", encoding="utf8") as out:
            print("DOTFILES =", *self.dotfiles, file=out)
            print("", file=out)
            print("%.png: %.dot", file=out)
            print("\tdot -T png $< -o $@", file=out)
            print("", file=out)
            print("report.html: report.rst $(DOTFILES:.dot=.png)", file=out)
            print("\trst2html $< $@", file=out)


    def generate_report(self, file=sys.stdout):
        self.print_title("Housekeeping report", "=", file=file)
        print(".. figure:: tasks.png", file=file)
        print("   :alt: task dependency graph", file=file)
        print("", file=file)
        print("   Dependencies and order of instantiation of tasks", file=file)
        print("", file=file)
        self.print_depgraph_legend(file=file)
        print("", file=file)

        # TODO: add task instantiation log extract

        print(".. figure:: stages.png", file=file)
        print("   :alt: stages dependency graph", file=file)
        print("", file=file)
        print("   Dependencies and order of execution of stages", file=file)
        print("", file=file)
        self.print_depgraph_legend(file=file)
        print("", file=file)

        for idx, stage in enumerate(self.hk.stage_schedule.sequence, start=1):
            stage = self.hk.stages[stage]
            self.print_title("Stage {}: {}".format(idx, stage.name), "-", file=file)
            print(".. figure:: stage-{}.png".format(stage.name), file=file)
            print("   :alt: task execution dependency graph", file=file)
            print("", file=file)
            print("   Dependencies and order of execution of tasks", file=file)
            print("", file=file)
            self.print_depgraph_legend(file=file)
            print("", file=file)

            # TODO: add task docstring
            # TODO: add task run info
            # TODO: add task log

    def generate_dotfiles(self):
        """
        Generate .dot files with dependency graphs
        """
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
        for stage in six.itervalues(self.hk.stages):
            with self.make_dotfile("stage-{}.dot".format(stage.name)) as out:
                print("digraph {} {{".format(stage.name), file=out)
                print('  label="Stage {}"'.format(stage.name), file=out)
                stage.task_schedule.make_dot(out)
                print("}", file=out)

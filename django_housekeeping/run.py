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
from .task import Task
from . import toposort
from .report import Report
from collections import defaultdict
import os
import os.path
import datetime
import sys
import time
import inspect
import logging

import six
if sys.version_info[0] >= 3: # Python 3
    global unicode
    unicode = str
    global xrange
    xrange = range

log = logging.getLogger(__name__)

class RunInfo(object):
    """
    Run a task and store info about its execution
    """
    def __init__(self, stage, task, mock=False):
        self.stage = stage
        self.task = task
        self.mock = mock
        self.executed = False
        self.skipped_reason = None
        self.exception = None
        self.success = False
        self.elapsed = None
        self.clock_start = time.clock()

    def set_success(self):
        self.elapsed = datetime.timedelta(seconds=time.clock() - self.clock_start)
        self.exception = None
        self.skipped_reason = None
        self.success = True
        self.executed = True
        log.info("%s:%s:run_%s: ran successfully, %s", self.stage.name, self.task.IDENTIFIER, self.stage.name, self.elapsed)

    def set_exception(self, type, value, traceback):
        self.elapsed = datetime.timedelta(seconds=time.clock() - self.clock_start)
        self.exception = (type, value, traceback)
        self.skipped_reason = None
        self.success = False
        self.executed = True
        log.info("%s:%s:run_%s: failed, %s", self.stage.name, self.task.IDENTIFIER, self.stage.name, self.elapsed)

    def set_skipped(self, reason):
        self.elapsed = datetime.timedelta(seconds=0.0)
        self.exception = None
        self.skipped_reason = reason
        self.success = False
        self.executed = False
        log.info("%s:%s:run_%s: skipped: %s", self.stage.name, self.task.IDENTIFIER, self.stage.name, self.skipped_reason)


class Schedule(object):
    def __init__(self):
        self.graph = defaultdict(set)
        self.sequence = None

    def add_node(self, node):
        self.graph.setdefault(node, set())

    def add_edge(self, node_prev, node_next):
        self.graph[node_prev].add(node_next)

    def schedule(self):
        self.sequence = toposort.sort(self.graph)

    def make_dot(self, out, formatter=unicode):
        for node in self.sequence:
            print('  "{}"'.format(formatter(node)), file=out)

        # Arcs that have been selected as the final sequence
        selected = set()
        for i in xrange(len(self.sequence) - 1):
            selected.add((self.sequence[i], self.sequence[i+1]))

        for prev, arcs in six.iteritems(self.graph):
            for next in arcs:
                if (prev, next) in selected:
                    selected.discard((prev, next))
                    style = " [color=red,penwidth=3.0]"
                else:
                    style = ""
                print('  "{}" -> "{}"{};'.format(formatter(prev), formatter(next), style), file=out)

        for prev, next in selected:
            print('  "{}" -> "{}" [color=red, style=dashed];'.format(formatter(prev), formatter(next)), file=out)

class Stage(object):
    def __init__(self, hk, name):
        self.hk = hk
        self.name = name
        self.tasks = {}
        self.task_schedule = Schedule()
        # Task execution results
        self.results = {}

    def add_task(self, task):
        self.tasks[task.IDENTIFIER] = task

    def schedule(self):
        """
        Compute the order of execution of tasks objects in this stage, and set
        self.task_sequence to the sorted list of Task objects
        """
        # Create nodes for all tasks
        for task in six.itervalues(self.tasks):
            self.task_schedule.add_node(task.IDENTIFIER)

        for task in six.itervalues(self.tasks):
            next = task.IDENTIFIER
            for prev in (x.IDENTIFIER for x in task.DEPENDS):
                if prev not in self.task_schedule.graph:
                    log.debug("%s: skipping dependency %s -> %s that does not seem to be relevant for this stage", self.name, prev, next)
                    continue
                self.task_schedule.add_edge(prev, next)

        self.task_schedule.schedule()

    def get_schedule(self):
        """
        Generate the list of tasks as they would be executed
        """
        for identifier in self.task_schedule.sequence:
            yield self.tasks[identifier]

    def get_results(self, task):
        """
        Return TaskExecution results for a task, or None if it has not been run
        """
        return self.results.get(task.IDENTIFIER, None)

    def reason_task_should_not_run(self, task, run_filter=None):
        """
        If the task can run, it returns None.
        Else it returns a string describing why the task should not run.
        """
        # Check if the task already ran
        if self.get_results(task) is not None:
            return "it has already been run"

        name = "{}:{}".format(self.name, task.IDENTIFIER)
        if run_filter and not run_filter(name):
            return "does to match current stage/task filter"

        # There is no need of checking dependencies recursively, since we don't
        # run a task unless all its dependencies have already been run
        # correctly
        for t in task.DEPENDS:
            # Ignore dependencies that do not want to run in this stage
            if t.IDENTIFIER not in self.tasks: continue
            exinfo = self.get_results(t)
            if exinfo is None:
                return "its dependency {} has not been run".format(t.IDENTIFIER)
            if not exinfo.executed:
                return "its dependency {} has not been run".format(t.IDENTIFIER)
            if not exinfo.success:
                return "its dependency {} has not run successfully".format(t.IDENTIFIER)
        return None

    def run_task(self, task, mock):
        run_info = RunInfo(self, task, mock=mock)

        # TODO: also store and log execution time

        meth_name = "run_{}".format(self.name)
        method = getattr(task, meth_name, None)
        if method is None:
            run_info.set_skipped("%s has no method %s", self.task.IDENTIFIER, meth_name)
            return run_info

        if mock:
            run_info.set_success()
        else:
            try:
                if not mock:
                    method(self)
            except KeyboardInterrupt:
                raise
            except:
                log.exception("%s: %s failed", task.IDENTIFIER, meth_name)
                run_info.set_exception(*sys.exc_info())
            else:
                run_info.set_success()

        return run_info

    def run(self, run_filter=None):
        for identifier in self.task_schedule.sequence:
            task = self.tasks[identifier]
            should_not_run = self.reason_task_should_not_run(task, run_filter=run_filter)
            if should_not_run is not None:
                run_info = RunInfo(self, task)
                run_info.set_skipped(should_not_run)
                self.results[identifier] = run_info
                continue
            mock = self.hk.test_mock and isinstance(task, self.hk.test_mock)
            self.results[identifier] = self.run_task(task, mock)


class Outdir(object):
    def __init__(self, root):
        self.root = root
        self.outdir = None

    def init(self, hk):
        # Ensure the root dir exists
        if not os.path.exists(self.root):
            log.warning("output directory %s does not exist: creating it", self.root)
            os.makedirs(self.root, 0o777)

        # Create a new directory for this maintenance run
        candidate = None
        while True:
            if candidate is None:
                candidate = os.path.join(self.root, datetime.datetime.utcnow().strftime("%Y%m%d"))
            else:
                time.sleep(0.5)
                candidate = os.path.join(self.root, datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S"))
            try:
                os.mkdir(candidate, 0o777)
                break
            except OSError as e:
                import errno
                if e.errno != errno.EEXIST:
                    raise

        self.outdir = candidate

    def path(self, relpath=None):
        """
        Make sure the given subpath exists inside the output directory, and
        return the full path to it
        """
        if relpath is None:
            return self.outdir
        res = os.path.join(self.outdir, relpath)
        if not os.path.exists(res):
            os.makedirs(res, 0o777)
        return res

    def cleanup(self):
        pass
        # TODO: optionally tar everything and remove the directory



class Housekeeping(object):
    """
    Housekeeping runner, that runs all Tasks from all installed apps
    """
    def __init__(self, outdir=None, dry_run=False, test_mock=None):
        """
        dry_run: if true, everything will be done except permanent changes
        outdir: root directory where we can create one directory for each
                housekeeping run, where the run output will be stored
        task_filter: set to a function to filter what tasks will be run. Note
                     that the dependencies of a task are run even if
                     task_filter refused them.
        test_mock: class or list of classes whose objects won't be run even if
                   they are dependencies of tasks that will be run. Used during
                   tests when you know what you are doing, for example to skip
                   a database backup phase.
        """

        self.dry_run = dry_run
        self.test_mock = test_mock
        if outdir is not None:
            self.outdir = Outdir(outdir)
        else:
            self.outdir = None
        self.report = None

        # All registered task classes
        self.task_classes = set()

        # Schedule for task instantiation
        self.task_schedule = Schedule()

        # Stage objects by name
        self.stages = {}

        # Stage run schedule
        self.stage_schedule = Schedule()

    def autodiscover(self):
        """
        Autodiscover tasks from django apps
        """
        from django.conf import settings
        from django.utils.importlib import import_module

        # Try to use the HOUSEKEEPING_ROOT Django setting to instantiate a
        # outdir, if we do not have one yet
        if self.outdir is None:
            outdir = getattr(settings, "HOUSEKEEPING_ROOT", None)
            if outdir is not None:
                self.outdir = Outdir(outdir)

        seen = set()
        for app_name in settings.INSTALLED_APPS:
            mod_name = "{}.housekeeping".format(app_name)
            try:
                mod = import_module(mod_name)
            except ImportError:
                continue
            log.debug("autodiscover: found module %s", mod_name)
            for cls_name, cls in inspect.getmembers(mod, inspect.isclass):
                if issubclass(cls, Task) and cls != Task:
                    if cls in seen: continue
                    seen.add(cls)
                    cls.IDENTIFIER = "{}.{}".format(app_name, cls_name)
                    log.debug("autodiscover: found task %s", cls.IDENTIFIER)
                    self.register_task(cls)

    def _register_stage_dependencies(self, stages):
        """
        Add stage information to the stage graph
        """
        # Add a node to the graph for each stage
        for s in stages:
            self.stage_schedule.add_node(s)
        # Add arches for each couple in the dependency chain
        for i in range(0, len(stages) - 1):
            self.stage_schedule.add_edge(stages[i], stages[i+1])

    def register_task(self, task_cls):
        """
        Instantiate a task and add it as an attribute of this object
        """
        if task_cls in self.task_classes:
            return

        # Make sure this class has an identifier
        if not task_cls.IDENTIFIER:
            task_cls.IDENTIFIER = "{}.{}".format(task_cls.__module__, task_cls.__name__)
        self.task_classes.add(task_cls)
        self.task_schedule.add_node(task_cls)

        for cls in task_cls.DEPENDS:
            self.register_task(cls)
            self.task_schedule.add_edge(cls, task_cls)

    def get_schedule(self):
        """
        Generate the list of tasks as they would be executed
        """
        for stage in self.stage_schedule.sequence:
            stage = self.stages[stage]
            for task in stage.get_schedule():
                yield stage, task

    def init(self):
        """
        Instantiate all Task objects, and schedule their execution
        """
        # Schedule task instantiation
        self.task_schedule.schedule()

        # Create output directory
        if self.outdir:
            self.outdir.init(self)
            self.report = Report(self)

        # Instantiate all tasks
        for task_cls in self.task_schedule.sequence:
            # Instantiate the task
            task = task_cls(self)

            # If the task has a name, add it as an attribute of the Housekeeping
            # object
            if task_cls.NAME is not None:
                if hasattr(self, task_cls.NAME):
                    raise Exception("Task {} instantiated twice".format(task_cls.NAME))
                log.debug("sharing task %s as %s", task.IDENTIFIER, task.NAME)
                setattr(self, task.NAME, task)

            # Add stage information to the stage graph
            self._register_stage_dependencies(task.get_stages())

            # Add the task to all its stages
            for name in task.get_stages():
                stage = self.stages.get(name, None)
                if stage is None:
                    self.stages[name] = stage = Stage(self, name)
                if hasattr(task, "run_{}".format(name)):
                    stage.add_task(task)

        # Schedule execution of stages and tasks
        self.stage_schedule.schedule()
        for stage in six.itervalues(self.stages):
            stage.schedule()

    def run(self, run_filter=None):
        """
        Run all tasks, collecting run statistics.

        If some dependency of a task did not run correctly, the task is
        skipped.
        """
        for stage in self.stage_schedule.sequence:
            self.stages[stage].run(run_filter=run_filter)

        if self.outdir:
            self.report.generate()
            self.outdir.cleanup()

    def list_run(self, run_filter=None):
        for stage, task in self.get_schedule():
            name = "{}:{}".format(stage.name, task.IDENTIFIER)
            if run_filter and not run_filter(name):
                continue
            yield(name)

    #def log_stats(self):
    #    for task in self.tasks:
    #        ex = self.get_results(task)
    #        if ex is None:
    #            log.info("%s: not run", task.IDENTIFIER)
    #        else:
    #            ex.log_stats()

    def make_dot(self, out):
        print("digraph TASKS {", file=out)
        print('  label="Tasks"', file=out)
        self.task_schedule.make_dot(out, formatter=lambda x:x.IDENTIFIER)
        print("}", file=out)

        print("digraph STAGES {", file=out)
        print('  label="Stages"', file=out)
        self.stage_schedule.make_dot(out)
        print("}", file=out)

        for stage in six.itervalues(self.stages):
            print("digraph {} {{".format(stage.name), file=out)
            print('  label="Stage {}"'.format(stage.name), file=out)
            stage.task_schedule.make_dot(out)
            print("}", file=out)

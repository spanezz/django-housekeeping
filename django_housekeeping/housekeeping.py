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
import sys
import time
import datetime
import inspect
import logging

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


class Stage(object):
    def __init__(self, hk, name):
        self.hk = hk
        self.name = name
        self.tasks = {}
        self.task_sequence = None
        # Task execution results
        self.results = {}

    def add_task(self, task):
        self.tasks[task.IDENTIFIER] = task

    def schedule(self):
        """
        Compute the order of execution of tasks objects in this stage, and set
        self.task_sequence to the sorted list of Task objects
        """
        # Task objects by class
        by_class = {}
        # Task classes dependency graph
        graph = {}
        # Create nodes for all tasks
        for task in self.tasks.itervalues():
            by_class[task.__class__] = task
            graph[task.__class__] = set()

        for task in self.tasks.itervalues():
            next = task.__class__
            for prev in task.DEPENDS:
                if prev not in graph:
                    log.debug("%s: skipping dependency %s -> %s that does not seem to be relevant for this stage", self.name, prev.IDENTIFIER, next.IDENTIFIER)
                    continue
                graph[prev].add(next)

        self.task_sequence = [by_class[x] for x in toposort.sort(graph)]

    def get_schedule(self):
        """
        Generate the list of tasks as they would be executed
        """
        for task in self.task_sequence:
            yield task

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
        for task in self.task_sequence:
            should_not_run = self.reason_task_should_not_run(task, run_filter=run_filter)
            if should_not_run is not None:
                run_info = RunInfo(self, task)
                run_info.set_skipped(should_not_run)
                self.results[task.IDENTIFIER] = run_info
                continue
            mock = self.hk.test_mock and isinstance(task, self.hk.test_mock)
            self.results[task.IDENTIFIER] = self.run_task(task, mock)

def schedule_task_classes(task_classes):
    graph = {}

    # Add nodes
    for cls in task_classes:
        graph[cls] = set()

    # Add arcs
    for cls in task_classes:
        for dep in cls.DEPENDS:
            graph[dep].add(cls)

    # Return the sorted schedule
    return toposort.sort(graph)


class Housekeeping(object):
    """
    Housekeeping runner, that runs all Tasks from all installed apps
    """
    def __init__(self, dry_run=False, test_mock=None):
        """
        dry_run: if true, everything will be done except permanent changes
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

        self.task_classes = set()

        # List of tasks for each stage
        self.stages = {}

        # Dependency graph for stages
        self.stage_graph = {}

        # Ordered sequence of stages
        self.stage_sequence = None

    def autodiscover(self):
        """
        Autodiscover tasks from django apps
        """
        from django.conf import settings
        from django.utils.importlib import import_module
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
            self.stage_graph.setdefault(s, set())
        # Add arches for each couple in the dependency chain
        for i in range(0, len(stages) - 1):
            self.stage_graph[stages[i]].add(stages[i+1])

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

        for cls in task_cls.DEPENDS:
            self.register_task(cls)

    def get_schedule(self):
        """
        Generate the list of tasks as they would be executed
        """
        for stage in self.stage_sequence:
            stage = self.stages[stage]
            for task in stage.get_schedule():
                yield stage, task

    def init(self):
        """
        Instantiate all Task objects, and schedule their execution
        """
        # Instantiate all tasks
        for task_cls in schedule_task_classes(self.task_classes):
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
        self.stage_sequence = toposort.sort(self.stage_graph)
        for stage in self.stages.itervalues():
            stage.schedule()


    def run(self, run_filter=None):
        """
        Run all tasks, collecting run statistics.

        If some dependency of a task did not run correctly, the task is
        skipped.
        """
        for stage in self.stage_sequence:
            self.stages[stage].run(run_filter=run_filter)

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

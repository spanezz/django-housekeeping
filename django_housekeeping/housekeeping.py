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
import inspect
import logging

log = logging.getLogger(__name__)

class TaskExecution(object):
    """
    Run a task and store info about its execution
    """
    def __init__(self, stage, task, mock=False):
        self.stage = stage
        self.task = task
        self.executed = False
        self.exception = None
        self.success = False
        self.mock = mock

    def run(self):
        # TODO: also store and log execution time
        try:
            if not self.mock:
                meth_name = "run_{}".format(self.stage.name)
                method = getattr(self.task, meth_name, None)
                if method is None:
                    log.error("%s has no method %s", self.task.IDENTIFIER, meth_name)
                else:
                    method(self.stage)
        except Exception as e:
            self.exception = e
            self.sucess = False
            log.exception("%s run failed", self.task.IDENTIFIER)
        else:
            self.exception = None
            self.success = True
        self.executed = True

    def log_stats(self):
        if self.executed:
            if self.success:
                log.info("%s: ran successfully", self.task.IDENTIFIER)
            else:
                log.info("%s: failed", self.task.IDENTIFIER)
        else:
            log.info("%s: not run", self.task.IDENTIFIER)
        self.task.log_stats()

class Stage(object):
    def __init__(self, hk, name):
        self.hk = hk
        self.name = name
        self.tasks = []
        self.task_sequence = None
        # Task execution results
        self.results = {}

    def add_task(self, task):
        self.tasks.append(task)

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
        for task in self.tasks:
            by_class[task.__class__] = task
            graph[task.__class__] = set()

        unsatisfied = False
        for task in self.tasks:
            next = task.__class__
            for prev in task.DEPENDS:
                if prev not in graph:
                    unsatisfied = True
                    log.error("%s depends on %s which does not run in stage %s", next, prev, self.name)
                    continue
                graph[prev].add(next)

        if unsatisfied:
            raise ValueError("unsatisfiable task dependencies in stage {}".format(self.name))

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

    def reason_task_should_not_run(self, task):
        """
        If the task can run, it returns None.
        Else it returns a string describing why the task should not run.
        """
        # Check if the task already ran
        if self.get_results(task) is not None:
            return "it has already been run"
        # There is no need of checking dependencies recursively, since we don't
        # run a task unless all its dependencies have already been run
        # correctly
        for t in task.DEPENDS:
            exinfo = self.get_results(t)
            if exinfo is None:
                return "its dependency {} has not been run".format(t.IDENTIFIER)
            if not exinfo.executed:
                return "its dependency {} has not been run".format(t.IDENTIFIER)
            if not exinfo.success:
                return "its dependency {} has not run successfully".format(t.IDENTIFIER)
        return None

    def run(self):
        for task in self.task_sequence:
            should_not_run = self.reason_task_should_not_run(task)
            if should_not_run is not None:
                log.info("%s cannot run: %s", task.IDENTIFIER, should_not_run)
                continue
            mock = self.hk.test_mock and isinstance(task, self.hk.test_mock)
            self.results[task.IDENTIFIER] = ex = TaskExecution(self, task, mock=mock)
            ex.run()


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

        # List of tasks for each stage
        self.stages = {}

        # Dependency graph for stages
        self.stage_graph = {}

        # Ordered sequence of stages
        self.stage_sequence = None

    def autodiscover(self, task_filter=None):
        """
        Autodiscover tasks from django apps
        """
        from django.conf import settings
        from django.utils.importlib import import_module
        for app_name in settings.INSTALLED_APPS:
            try:
                mod = import_module("{}.housekeeping".format(app_name))
            except ImportError:
                continue
            for cls_name, cls in inspect.getmembers(mod, inspect.isclass):
                if issubclass(cls, Task) and cls != Task:
                    cls.IDENTIFIER = "{}.{}".format(app_name, cls_name)
                    # Skip tasks that the filter does not want
                    if task_filter is not None and not task_filter(cls):
                        continue
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
            log.debug("New stage dependency: %s -> %s", stages[i], stages[i+1])
            self.stage_graph[stages[i]].add(stages[i+1])

    def register_task(self, task_cls):
        """
        Instantiate a task and add it as an attribute of this object
        """
        # Make sure this class has an identifier
        if not task_cls.IDENTIFIER:
            task_cls.IDENTIFIER = "{}.{}".format(task_cls.__module__, task_cls.__name__)

        # Instantiate the task
        task = task_cls(self)

        # If the task has a name, add it as an attribute of the Housekeeping
        # object
        if task_cls.NAME is not None:
            if hasattr(self, task_cls.NAME):
                raise Exception("Task {} instantiated twice".format(task_cls.NAME))
            log.debug("sharing task object %s as %s", task_cls, task_cls.NAME)
            setattr(self, task_cls.NAME, task)

        # Add stage information to the stage graph
        self._register_stage_dependencies(task.get_stages())

        # Add the task to all its stages
        for name in task.get_stages():
            stage = self.stages.get(name, None)
            if stage is None:
                self.stages[name] = stage = Stage(self, name)
            if hasattr(task, "run_{}".format(name)):
                stage.add_task(task)

    def schedule(self):
        """
        Schedule execution of stages and tasks
        """
        self.stage_sequence = toposort.sort(self.stage_graph)
        for stage in self.stages.itervalues():
            stage.schedule()

    def get_schedule(self):
        """
        Generate the list of tasks as they would be executed
        """
        for stage in self.stage_sequence:
            for task in self.stages[stage].get_schedule():
                yield stage, task

    def run(self):
        """
        Run all tasks, collecting run statistics.

        If some dependency of a task did not run correctly, the task is
        skipped.
        """
        if self.stage_sequence is None:
            self.schedule()

        for stage in self.stage_sequence:
            self.stages[stage].run()

    def log_stats(self):
        for task in self.tasks:
            ex = self.get_results(task)
            if ex is None:
                log.info("%s: not run", task.IDENTIFIER)
            else:
                ex.log_stats()

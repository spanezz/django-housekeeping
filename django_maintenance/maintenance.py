# Pluggable maintenance framework for Django sites
#
# Copyright (C) 2013  Enrico Zini <enrico@enricozini.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from . import MaintenanceTask
from django.conf import settings
from django.utils.importlib import import_module
import inspect
import logging

log = logging.getLogger(__name__)

class TaskExpander(object):
    """
    Recursively expand components including each component's dependencies.

    Each component (including dependencies) will only be included once in the
    resulting list
    """
    def __init__(self, items=[]):
        self.seen = set()
        self.result = []
        for c in items:
            self.add(c)

    def add(self, comp):
        if comp in self.seen:
            return

        for c in comp.DEPENDS:
            self.add(c)

        self.result.append(comp)
        self.seen.add(comp)

class TaskExecution(object):
    """
    Run a task and store info about its execution
    """
    def __init__(self, task):
        self.task = task
        self.executed = False
        self.exception = None
        self.success = False

    def run(self):
        # TODO: also store and log execution time
        try:
            self.task.run()
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

class Maintenance(object):
    """
    Maintenance runner, that runs all MaintenanceTasks from all installed apps
    """
    def __init__(self, dry_run=False, task_filter=None):
        self.dry_run = dry_run

        # List of tasks, partially sorted so that dependencies come before the
        # tasks that need them
        self.tasks = []
        for task_cls in TaskExpander(self.find_tasks()).result:
            # Skip tasks that the filter does not want
            if task_filter is not None and not task_filter(task_cls):
                continue
            self.register_task(task_cls)

        # Task execution results
        self.results = {}

    def register_task(self, task_cls):
        """
        Instantiate a task and add it as an attribute of this object
        """
        task = task_cls(self)
        self.tasks.append(task)
        if task_cls.NAME is not None:
            if hasattr(self, task_cls.NAME):
                raise Exception("Task {} instantiated twice".format(task_cls.NAME))
            setattr(self, task_cls.NAME, task)

    def find_tasks(self):
        """
        Generate all MaintenanceTask subclasses found in installed apps
        """
        for app_name in settings.INSTALLED_APPS:
            try:
                mod = import_module("{}.maintenance".format(app_name))
            except ImportError:
                continue
            for cls_name, cls in inspect.getmembers(mod, inspect.isclass):
                if issubclass(cls, MaintenanceTask) and cls != MaintenanceTask:
                    cls.IDENTIFIER = "{}.{}".format(app_name, cls_name)
                    yield cls

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
        """
        Run all tasks, collecting run statistics.

        If some dependency of a task did not run correctly, the task is
        skipped.
        """
        for task in self.tasks:
            should_not_run = self.reason_task_should_not_run(task)
            if should_not_run is not None:
                log.info("%s cannot run: %s", task.IDENTIFIER, should_not_run)
                continue
            self.results[task.IDENTIFIER] = ex = TaskExecution(task)
            ex.run()

    def log_stats(self):
        for task in self.tasks:
            ex = self.get_results(task)
            if ex is None:
                log.info("%s: not run", task.IDENTIFIER)
            else:
                ex.log_stats()

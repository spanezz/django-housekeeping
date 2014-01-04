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

from django.core.management.base import BaseCommand, CommandError
from django_maintenance.maintenance import Maintenance
import optparse
import datetime
import sys
import logging

log = logging.getLogger(__name__)

class TaskFilter(object):
    def __init__(self, include, exclude):
        self.include = include
        self.exclude = exclude

    def __call__(self, task):
        import fnmatch
        if self.include is not None:
            for pattern in self.include:
                if not fnmatch.fnmatch(task.IDENTIFIER, pattern):
                    return False
        if self.exclude is not None:
            for pattern in self.exclude:
                if fnmatch.fnmatch(task.IDENTIFIER, pattern):
                    return False
        return True


class Command(BaseCommand):
    help = 'Run site maintenance'
    option_list = BaseCommand.option_list + (
        optparse.make_option("--quiet", action="store_true", dest="quiet", default=None,
                             help="Disable progress reporting"),
        optparse.make_option("--dry-run", action="store_true", dest="dry_run", default=None,
                             help="Go through all the motions without making any changes"),
        optparse.make_option("--include", action="append", dest="include", default=None,
                             help="Include tasks matching this shell-like pattern. Can be used multiple times."),
        optparse.make_option("--exclude", action="append", dest="exclude", default=None,
                             help="Exclude tasks matching this shell-like pattern. Can be used multiple times."),
        optparse.make_option("--list", action="store_true", dest="do_list", default=False,
                             help="List all available tasks"),
        optparse.make_option("--logfile", action="store", dest="logfile", default=None,
                             help="Also log all messages to the given file. You can use strftime escape sequences."),
        optparse.make_option("--logfile-debug", action="store_true", dest="logfile_debug", default=False,
                             help="Also log debug messages to the log file"),
    )

    def handle(self, quiet=False, dry_run=False, include=None, exclude=None, logfile=None, logfile_debug=False, do_list=False, *args, **opts):
        FORMAT = "%(asctime)-15s %(levelname)s %(message)s"
        handlers = []

        # If create a file logger, if requested
        if logfile:
            fname = datetime.datetime.utcnow().strftime(logfile)
            file_handler = logging.FileHandler(fname, encoding="utf8")
            file_handler.setFormatter(logging.Formatter(FORMAT))
            if logfile_debug:
                file_handler.setLevel(logging.DEBUG)
            else:
                file_handler.setLevel(logging.INFO)
            handlers.append(file_handler)

        # And a stderr logger
        stderr_handler = logging.StreamHandler(stream=sys.stderr)
        stderr_handler.setFormatter(logging.Formatter(FORMAT))
        if quiet:
            stderr_handler.setLevel(logging.WARNING)
        else:
            stderr_handler.setLevel(logging.INFO)
        handlers.append(stderr_handler)

        root_logger = logging.getLogger("")
        for h in handlers:
            root_logger.addHandler(h)
        root_logger.setLevel(min(x.level for x in handlers))

        task_filter = None
        if include is not None or exclude is not None:
            task_filter = TaskFilter(include, exclude)
        maint = Maintenance(dry_run=dry_run, task_filter=task_filter)
        if do_list:
            for task in maint.tasks:
                print(task.IDENTIFIER)
        else:
            maint.run()
            maint.log_stats()

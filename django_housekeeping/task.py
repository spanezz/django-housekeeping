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

class Task(object):
    """
    A housekeeping task. Any subclass of this in an appname.housekeeping module
    will be automatically found and run during housekeeping
    """
    # Define NAME to have this task made available to other tasks as a member
    # of Housekeeping
    NAME = None

    # Unique, human and machine readable identifier for this task,
    # automatically filled by Housekeeping during task discovery
    IDENTIFIER = None

    # Task classes that should be run before this one
    DEPENDS = []

    def __init__(self, maint, **kw):
        """
        Constructor

        maint: the Housekeeping object
        """
        self.maint = maint

    def run(self):
        """
        Run this housekeeping task
        """
        pass

    def log_stats(self):
        """
        Log statistics about this task's execution
        """
        pass



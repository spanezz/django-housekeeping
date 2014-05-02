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
import inspect

# Order of stages.
#
# For any string listed here, a run_$STRING method will be called, in the
# same order as the STAGES list.
#
# In each stage, tasks are run in dependency order.
STAGES = ["main"]

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

    def __init__(self, hk, **kw):
        """
        Constructor

        hk: the Housekeeping object
        """
        self.hk = hk

    #def run_main(self, stage):
    #    """
    #    Run this housekeeping task
    #    """
    #    pass

    def get_stages(self):
        """
        Get the ordered list of stages for this task.
        """
        # First look in the object or its class
        res = getattr(self, "STAGES", None)
        if res is not None: return res

        module = inspect.getmodule(self.__class__)

        # If that fails, look in the module
        res = getattr(module, "STAGES", None)
        if res is not None: return res

        # If that fails, return a default
        return ("main", )

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

class MaintenanceTask(object):
    """
    A maintenance task. Any subclass of this in an appname.maintenance module
    will be automatically found and run during maintenance
    """
    # Define NAME to have this task made available to other tasks as a member
    # of Maintenance
    NAME = None

    # Unique, human and machine readable identifier for this task,
    # automatically filled by Maintenance during task discovery
    IDENTIFIER = None

    # MaintenanceTask classes that should be run before this one
    DEPENDS = []

    def __init__(self, maint, **kw):
        """
        Constructor

        maint: the Maintenance object
        """
        self.maint = maint

    def run(self):
        """
        Run this maintenance task
        """
        pass

    def log_stats(self):
        """
        Log statistics about this task's execution
        """
        pass



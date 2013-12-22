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
import sys
import logging

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run site maintenance'
    option_list = BaseCommand.option_list + (
        optparse.make_option("--quiet", action="store_true", dest="quiet", default=None, help="Disable progress reporting"),
        optparse.make_option("--dry-run", action="store_true", dest="dry_run", default=None, help="Go through all the motions without making any changes"),
    )

    def handle(self, quiet=False, *args, **opts):
        FORMAT = "%(asctime)-15s %(levelname)s %(message)s"
        if quiet:
            logging.basicConfig(level=logging.WARNING, stream=sys.stderr, format=FORMAT)
        else:
            logging.basicConfig(level=logging.INFO, stream=sys.stderr, format=FORMAT)

        maint = Maintenance()
        maint.run()
        maint.log_stats()

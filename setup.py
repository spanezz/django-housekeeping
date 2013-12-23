#!/usr/bin/env/python
"""
Copyright (C) 2013 Enrico Zini <enrico@enricozini.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from distutils.core import setup

setup(
    name = "django_maintenance",
    version = "0.1",
    description = "Pluggable maintenance framework for Django sites",
    author = ["Enrico Zini"],
    author_email = ["enrico@enricozini.org"],
    url = "http://git.debian.org/?p=users/enrico/django_maintenance.git",
    license = "http://www.gnu.org/licenses/agpl-3.0.html",
    packages = ["django_maintenance"],
)

#!/usr/bin/env/python
# coding: utf8
"""
Copyright (C) 2013--2014 Enrico Zini <enrico@enricozini.org>

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 3.0 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library.
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from distutils.core import setup

setup(
    name = "django_housekeeping",
    version = "1.0",
    description = "Pluggable housekeeping framework for Django sites",
    author = ["Enrico Zini"],
    author_email = ["enrico@enricozini.org"],
    url = "https://github.com/spanezz/django-housekeeping",
    license = "https://www.gnu.org/licenses/lgpl.html",
    packages = ["django_housekeeping",
                "django_housekeeping.management",
                "django_housekeeping.management.commands"]
)

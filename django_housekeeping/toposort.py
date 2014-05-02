# coding: utf8
# Pluggable housekeeping framework for Django sites
#
# Copyright (C) 2014  Enrico Zini <enrico@enricozini.org>
# Based on code by Paul Harrison and Dries Verdegem released under the Public
# Domain.
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

# From: http://www.logarithmic.net/pfh/blog/01208083168
# and: http://www.logarithmic.net/pfh-files/blog/01208083168/tarjan.py
def strongly_connected_components(graph):
    """
    Tarjan's Algorithm (named for its discoverer, Robert Tarjan) is a graph theory algorithm
    for finding the strongly connected components of a graph.

    Based on: http://en.wikipedia.org/wiki/Tarjan%27s_strongly_connected_components_algorithm
    """

    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    result = []

    def strongconnect(node):
        # set the depth index for this node to the smallest unused index
        index[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)

        # Consider successors of `node`
        successors = graph.get(node, ())
        for successor in successors:
            if successor not in lowlinks:
                # Successor has not yet been visited; recurse on it
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif successor in stack:
                # the successor is in the stack and hence in the current strongly connected component (SCC)
                lowlinks[node] = min(lowlinks[node], index[successor])

        # If `node` is a root node, pop the stack and generate an SCC
        if lowlinks[node] == index[node]:
            connected_component = []

            while True:
                successor = stack.pop()
                connected_component.append(successor)
                if successor == node: break

            # storing the result
            result.append(connected_component)

    for node in graph:
        if node not in lowlinks:
            strongconnect(node)

    return result


def topological_sort(graph):
    count = {}
    for node in graph:
        count[node] = 0
    for node in graph:
        for successor in graph[node]:
            count[successor] += 1

    ready = [node for node in graph if count[node] == 0]

    result = []
    while ready:
        node = ready.pop(-1)
        result.append(node)

        for successor in graph[node]:
            count[successor] -= 1
            if count[successor] == 0:
                ready.append(successor)

    return result


def sort(graph):
    """
    Linearize a dependency graph, throwing an exception if a cycle is detected
    """
    # Compute the strongly connected components, throwing an exception if we
    # see cycles
    cycles = []
    for items in strongly_connected_components(graph):
        if len(items) > 1:
            cycles.append("({})".format(", ".join(unicode(x) for x in items)))

    if cycles:
        if len(cycles) > 1:
            raise ValueError("{} cycles detected: {}".format(len(cycles), ", ".join(cycles)))
        else:
            raise ValueError("cycle detected: {}".format(cycles[0]))

    # We know that the graph does not have cycles, so we can run
    # topological_sort on it
    return topological_sort(graph)

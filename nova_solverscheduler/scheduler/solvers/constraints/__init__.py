# Copyright (c) 2014 Cisco Systems, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Constraints for scheduler constraint solvers
"""

from nova import loadables
from nova.scheduler import filters


class BaseConstraint(object):
    """Base class for constraints."""

    precedence = 0

    def get_components(self, variables, hosts, filter_properties):
        """Return the components of the constraint."""
        raise NotImplementedError()


class BaseLinearConstraint(BaseConstraint):
    """Base class of LP constraint."""

    def __init__(self):
        self._reset()

    def _reset(self):
        self.variables = []
        self.coefficients = []
        self.constants = []
        self.operators = []

    def _generate_components(self, variables, hosts, filter_properties):
        # override in a sub class
        pass

    def get_components(self, variables, hosts, filter_properties):
        # deprecated currently, reserve for future use
        self._reset()
        self._generate_components(variables, hosts, filter_properties)
        return (self.variables, self.coefficients, self.constants,
                self.operators)

    def get_constraint_matrix(self, hosts, filter_properties):
        raise NotImplementedError()


class BaseFilterConstraint(BaseLinearConstraint):
    """Base class for constraints that correspond to 1-time host filters."""

    # override this in sub classes
    host_filter_cls = filters.BaseHostFilter

    def __init__(self):
        super(BaseFilterConstraint, self).__init__()
        self.host_filter = self.host_filter_cls()

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        for i in xrange(num_hosts):
            host_passes = self.host_filter.host_passes(
                                            hosts[i], filter_properties)
            if not host_passes:
                constraint_matrix[i] = [False for j in xrange(num_instances)]

        return constraint_matrix


class ConstraintHandler(loadables.BaseLoader):
    def __init__(self):
        super(ConstraintHandler, self).__init__(BaseConstraint)


def all_constraints():
    """Return a list of constraint classes found in this directory.
    This method is used as the default for available constraints for
    scheduler and returns a list of all constraint classes available.
    """
    return ConstraintHandler().get_all_classes()

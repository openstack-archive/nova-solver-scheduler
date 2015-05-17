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
Costs for scheduler constraint solvers
"""

from nova import loadables


class BaseCost(object):
    """Base class for cost."""

    precedence = 0

    def cost_multiplier(self):
        """How weighted this cost should be.

        Override this method in a subclass, so that the returned value is
        read from a configuration option to permit operators specify a
        multiplier for the cost.
        """
        return 1.0

    def get_components(self, variables, hosts, filter_properties):
        """Return the components of the cost."""
        raise NotImplementedError()


class BaseLinearCost(BaseCost):
    """Base class of LP cost."""

    def __init__(self):
        self.variables = []
        self.coefficients = []

    def _generate_components(self, variables, hosts, filter_properties):
        # override in a sub class.
        pass

    def get_components(self, variables, hosts, filter_properties):
        # deprecated currently, reserve for future use
        self._generate_components(variables, hosts, filter_properties)
        return (self.variables, self.coefficients)

    def get_extended_cost_matrix(self, hosts, filter_properties):
        raise NotImplementedError()

    def get_init_costs(self, hosts, filter_properties):
        x_cost_mat = self.get_extended_cost_matrix(hosts, filter_properties)
        init_costs = [row[0] for row in x_cost_mat]
        return init_costs

    def get_cost_matrix(self, hosts, filter_properties):
        x_cost_mat = self.get_extended_cost_matrix(hosts, filter_properties)
        cost_matrix = [row[1:] for row in x_cost_mat]
        return cost_matrix


class CostHandler(loadables.BaseLoader):
    def __init__(self):
        super(CostHandler, self).__init__(BaseCost)


def all_costs():
    """Return a list of cost classes found in this directory.
    This method is used as the default for available costs for scheduler
    and should return a list of all cost classes available.
    """

    return CostHandler().get_all_classes()

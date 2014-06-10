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
Linear constraints for scheduler linear constraint solvers
"""

from nova import loadables


class BaseLinearConstraint(object):
    """Base class for linear constraint."""
    # The linear constraint should be formed as:
    # coeff_vector * var_vector' <operator> <constants>
    # where <operator> is ==, >, >=, <, <=, !=, etc.
    # For convenience, the <constants> can be merged into left-hand-side,
    # thus the right-hand-side is always 0.
    def __init__(self, variables, hosts, instance_uuids, request_spec,
                filter_properties):
        pass

    def get_coefficient_vectors(self, variables, hosts, instance_uuids,
                                request_spec, filter_properties):
        """Retruns a list of coefficient vectors."""
        raise NotImplementedError()

    def get_variable_vectors(self, variables, hosts, instance_uuids,
                            request_spec, filter_properties):
        """Returns a list of variable vectors."""
        raise NotImplementedError()

    def get_operations(self, variables, hosts, instance_uuids, request_spec,
                        filter_properties):
        """Returns a list of operations."""
        raise NotImplementedError()


class ResourceAllocationConstraint(BaseLinearConstraint):
    """Base class of resource allocation constraints."""

    def __init__(self, variables, hosts, instance_uuids, request_spec,
                 filter_properties):
        [self.num_hosts, self.num_instances] = self._get_host_instance_nums(
            hosts, instance_uuids, request_spec)

    def _get_host_instance_nums(self, hosts, instance_uuids, request_spec):
        """This method calculates number of hosts and instances."""
        num_hosts = len(hosts)
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
        return [num_hosts, num_instances]


class LinearConstraintHandler(loadables.BaseLoader):
    def __init__(self):
        super(LinearConstraintHandler, self).__init__(BaseLinearConstraint)


def all_linear_constraints():
    """Return a list of lineear constraint classes found in this directory.
    This method is used as the default for available linear constraints for
    scheduler and returns a list of all linearconstraint classes available.
    """
    return LinearConstraintHandler().get_all_classes()

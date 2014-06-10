# Copyright (c) 2014 Cisco Systems Inc.
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

from nova.openstack.common import log as logging
from nova.scheduler.solvers import linearconstraints

LOG = logging.getLogger(__name__)


class NonTrivialSolutionConstraint(linearconstraints.BaseLinearConstraint):
    """Constraint that forces each instance to be placed
    at exactly one host, so as to avoid trivial solutions.
    """

    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) (constants)
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the (constants) is merged into left-hand-side,
    # thus the right-hand-side is 0.

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

    def get_coefficient_vectors(self, variables, hosts, instance_uuids,
                                request_spec, filter_properties):
        # The coefficient for each variable is 1 and
        # constant in each constraint is (-1).
        coefficient_vectors = [[1 for i in range(self.num_hosts)] + [-1]
                                for j in range(self.num_instances)]
        return coefficient_vectors

    def get_variable_vectors(self, variables, hosts, instance_uuids,
                            request_spec, filter_properties):
        # The variable_matrix[i,j] denotes the relationship between
        # instance[i] and host[j]
        variable_vectors = []
        variable_vectors = [[variables[i][j] for i in range(self.num_hosts)] +
                            [1] for j in range(self.num_instances)]
        return variable_vectors

    def get_operations(self, variables, hosts, instance_uuids, request_spec,
                        filter_properties):
        # Operations are '=='.
        operations = [(lambda x: x == 0) for j in range(self.num_instances)]
        return operations

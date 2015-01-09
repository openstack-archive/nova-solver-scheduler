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

from nova.openstack.common import log as logging
from nova.scheduler.solvers import linearconstraints

LOG = logging.getLogger(__name__)


class ServerGroupAntiAffinityConstraint(linearconstraints.AffinityConstraint):
    """Force to select hosts which host given server group."""

    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) constant_vector
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the constant_vector is merged into left-hand-side,
    # thus the right-hand-side is always 0.

    def __init__(self, *args, **kwargs):
        super(ServerGroupAntiAffinityConstraint, self).__init__(
                                                            *args, **kwargs)
        self.policy_name = 'anti-affinity'

    def get_coefficient_vectors(self, variables, hosts, instance_uuids,
                                request_spec, filter_properties):
        coefficient_vectors = []
        policies = filter_properties.get('group_policies', [])
        if self.policy_name not in policies:
            coefficient_vectors = [[0 for j in range(self.num_instances)] + [0]
                                    for i in range(self.num_hosts)]
            return coefficient_vectors

        group_hosts = filter_properties.get('group_hosts')
        for host in hosts:
            if host.host in group_hosts:
                coefficient_vectors.append([1 for j
                                        in range(self.num_instances)] + [1])
            else:
                coefficient_vectors.append([1 for j
                                        in range(self.num_instances)] + [0])
        return coefficient_vectors

    def get_variable_vectors(self, variables, hosts, instance_uuids,
                            request_spec, filter_properties):
        variable_vectors = []
        variable_vectors = [[variables[i][j] for j in range(
                    self.num_instances)] + [1] for i in range(self.num_hosts)]
        return variable_vectors

    def get_operations(self, variables, hosts, instance_uuids,
                        request_spec, filter_properties):
        operations = [(lambda x: x <= 1) for i in range(self.num_hosts)]
        return operations

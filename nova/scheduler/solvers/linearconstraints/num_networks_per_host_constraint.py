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

from oslo.config import cfg

from nova.openstack.common import log as logging
from nova.scheduler.solvers import linearconstraints

max_host_networks_opts = [
    cfg.IntOpt('max_networks_per_host',
            default=4094,
            help='The maximum number of networks allowed in a host')
    ]

CONF = cfg.CONF
CONF.register_opts(max_host_networks_opts)

LOG = logging.getLogger(__name__)


class NumNetworksPerHostConstraint(
        linearconstraints.BaseLinearConstraint):
    """Constraint that specifies the maximum number of networks that
    each host can launch.
    """

    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) (constants)
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the (constants) is merged into left-hand-side,
    # thus the right-hand-side is 0.

    def get_coefficient_vectors(self, variables, hosts, instance_uuids,
                                request_spec, filter_properties):
        """Calculate the coeffivient vectors."""
        # The coefficient for each variable is 1 and constant in
        # each constraint is -(max_instances_per_host)
        usable_network_nums = [self._get_usable_network_num(hosts[i])
                for i in range(self.num_hosts)]
        requested_networks = filter_properties.get('requested_networks', None)
        num_new_networks = [0 for i in range(self.num_hosts)]
        for i in range(self.num_hosts):
            for network_id, requested_ip, port_id in requested_networks:
                if network_id:
                    if network_id not in hosts[i].networks:
                        num_new_networks[i] += 1

        coefficient_vectors = [
                [num_new_networks[i] - usable_network_nums[i]
                for j in range(self.num_instances)]
                for i in range(self.num_hosts)]
        return coefficient_vectors

    def get_variable_vectors(self, variables, hosts, instance_uuids,
                            request_spec, filter_properties):
        """Reorganize the variables."""
        # The variable_matrix[i,j] denotes the relationship between
        # host[i] and instance[j].
        variable_vectors = []
        variable_vectors = [[variables[i][j] for j in range(
                    self.num_instances)] for i in range(self.num_hosts)]
        return variable_vectors

    def get_operations(self, variables, hosts, instance_uuids, request_spec,
                        filter_properties):
        """Set operations for each constraint function."""
        # Operations are '<='.
        operations = [(lambda x: x <= 0) for i in range(self.num_hosts)]
        return operations

    def _get_usable_network_num(self, host_state):
        """This method returns the usable number of network
           for the given host.
        """
        num_networks = len(host_state.networks)
        max_networks_allowed = CONF.max_networks_per_host
        usable_network_num = max_networks_allowed - num_networks
        return usable_network_num

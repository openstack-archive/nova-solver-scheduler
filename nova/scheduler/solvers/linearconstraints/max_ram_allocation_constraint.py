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

from nova.scheduler.solvers import linearconstraints

CONF = cfg.CONF


class MaxRamAllocationPerHostConstraint(
        linearconstraints.ResourceAllocationConstraint):
    """Constraint of the total ram demand acceptable on each host."""

    # The linear constraint should be formed as:
    # coeff_vectors * var_vectors' (operator) (constants)
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the (constants) is merged into left-hand-side,
    # thus the right-hand-side is 0.

    def get_coefficient_vectors(self, variables, hosts, instance_uuids,
                                request_spec, filter_properties):
        # Give demand as coefficient for each variable and -supply as constant
        # in each constraint.
        [num_hosts, num_instances] = self._get_host_instance_nums(hosts,
                                          instance_uuids, request_spec)
        demand = [self._get_required_memory_mb(filter_properties)
                  for j in range(self.num_instances)]
        supply = [self._get_usable_memory_mb(hosts[i])
                  for i in range(self.num_hosts)]
        coefficient_vectors = [demand + [-supply[i]]
                               for i in range(self.num_hosts)]
        return coefficient_vectors

    def get_variable_vectors(self, variables, hosts, instance_uuids,
                             request_spec, filter_properties):
        # The variable_vectors[i,j] denotes the relationship between host[i]
        # and instance[j].
        variable_vectors = []
        variable_vectors = [[variables[i][j]
                             for j in range(self.num_instances)]
                            + [1] for i in range(self.num_hosts)]
        return variable_vectors

    def get_operations(self, variables, hosts, instance_uuids, request_spec,
                       filter_properties):
        # Operations are '<='.
        operations = [(lambda x: x <= 0) for i in range(self.num_hosts)]
        return operations

    def _get_usable_memory_mb(self, host_state):
        """This method returns the usable memory in mb for the given host.
           Takes into account the ram allocation ratio (Virtual ram to
           physical ram allocation ratio)
        """
        free_ram_mb = host_state.free_ram_mb
        total_usable_ram_mb = host_state.total_usable_ram_mb
        memory_mb_limit = total_usable_ram_mb * CONF.ram_allocation_ratio
        used_ram_mb = total_usable_ram_mb - free_ram_mb
        usable_ram_mb = memory_mb_limit - used_ram_mb
        return usable_ram_mb

    def _get_required_memory_mb(self, filter_properties):
        """This method returns the required memory in mb from
           the given filter_properties dictionary object.
        """
        required_ram_mb = 0
        instance_type = filter_properties.get('instance_type')
        if instance_type is not None:
            required_ram_mb = instance_type.get('memory_mb', 0)
        return required_ram_mb

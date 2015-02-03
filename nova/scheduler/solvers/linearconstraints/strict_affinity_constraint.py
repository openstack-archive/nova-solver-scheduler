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

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler.solvers import linearconstraints
from nova import servicegroup

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

class StrictAffinityConstraint(linearconstraints.BaseLinearConstraint):
    """A constraint to ensure that all the VMs must get placed to a single host only.
        There will be no placement solution if this is not possible."""

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
        """Retruns a list of coefficient vectors."""
        pass

    def get_variable_vectors(self, variables, hosts, instance_uuids,
                            request_spec, filter_properties):
        """Returns a list of variable vectors."""
        pass

    def get_operations(self, variables, hosts, instance_uuids, request_spec,
                        filter_properties):
        """Returns a list of operations."""
        return []

    def update_prob_variable(self, variables, hosts, instance_uuids, request_spec,
                        filter_properties, prob):
        column_sum_var = []
        for i in range(num_hosts):
            column_sum_var.append(pulp.LpVariable("Normalised_Column_Sum_Host_"+str(i), 0, 1, constants.LpInteger))

        #Adding normalisation constraint
        for i in range(num_hosts):
            prob += pulp.lpSum([variables[i][j]] for j in range(num_instances)) <= num_instances*column_sum_var[i]
            prob += column_sum_var[i] <= pulp.lpSum([variables[i][j]] for j in range(num_instances))

        #Sum of all normalised_column_sum_host variables must be 1.
        #This will ensure only 1 host is picked for all the VMs.s    
        prob += pulp.lpSum([column_sum_var[i]] for i in range(num_hosts)) == 1
        return prob
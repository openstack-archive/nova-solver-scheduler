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

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler.solvers import linearconstraints
from nova import servicegroup

LOG = logging.getLogger(__name__)


class AllHostsConstraint(linearconstraints.BaseLinearConstraint):
    """NoOp constraint. Passes all hosts."""

    # The linear constraint should be formed as:
    # coeff_vector * var_vector' <operator> <constants>
    # where <operator> is ==, >, >=, <, <=, !=, etc.

    def __init__(self, variables, hosts, instance_uuids, request_spec,
                filter_properties):
        self.servicegroup_api = servicegroup.API()
        [self.num_hosts, self.num_instances] = self._get_host_instance_nums(
                                        hosts, instance_uuids, request_spec)
        self._check_variables_size(variables)

    def _get_host_instance_nums(self, hosts, instance_uuids, request_spec):
        """This method calculates number of hosts and instances."""
        num_hosts = len(hosts)
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
        return [num_hosts, num_instances]

    def _check_variables_size(self, variables):
        """This method checks the size of variable matirx."""
        # Supposed to be a <num_hosts> by <num_instances> matrix.
        if len(variables) != self.num_hosts:
            raise ValueError(_('Variables row length should match'
                                'number of hosts.'))
        for row in variables:
            if len(row) != self.num_instances:
                raise ValueError(_('Variables column length should'
                                    'match number of instances.'))
        return True

    def get_coefficient_vectors(self, variables, hosts, instance_uuids,
                                request_spec, filter_properties):
        """Calculate the coeffivient vectors."""
        # Coefficients are 0 for active hosts and 1 otherwise
        coefficient_vectors = []
        for host in hosts:
            coefficient_vectors.append([0 for j in range(self.num_instances)])
        return coefficient_vectors

    def get_variable_vectors(self, variables, hosts, instance_uuids,
                            request_spec, filter_properties):
        """Reorganize the variables."""
        # The variable_vectors[i][j] denotes the relationship between host[i]
        # and instance[j].
        variable_vectors = []
        variable_vectors = [[variables[i][j] for j in
                    range(self.num_instances)] for i in range(self.num_hosts)]
        return variable_vectors

    def get_operations(self, variables, hosts, instance_uuids, request_spec,
                        filter_properties):
        """Set operations for each constraint function."""
        # Operations are '=='.
        operations = [(lambda x: x == 0) for i in range(self.num_hosts)]
        return operations

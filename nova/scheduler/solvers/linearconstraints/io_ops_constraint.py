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

from nova.compute import api as compute
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler.solvers import linearconstraints

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('max_io_ops_per_host', 'nova.scheduler.filters.io_ops_filter')


class IoOpsConstraint(linearconstraints.BaseLinearConstraint):
    """A constraint to ensure only those hosts are selected whose number of
    concurrent I/O operations are within a set threshold.
    """

    def __init__(self, variables, hosts, instance_uuids, request_spec,
                filter_properties):
        self.compute_api = compute.API()
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

    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) constant_vector
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the constant_vector is merged into left-hand-side,
    # thus the right-hand-side is always 0.

    def get_coefficient_vectors(self, variables, hosts, instance_uuids,
                                request_spec, filter_properties):
        # Coefficients are 0 for hosts within the limit and 1 for other hosts.
        coefficient_vectors = []
        for host in hosts:
            num_io_ops = host.num_io_ops
            max_io_ops = CONF.max_io_ops_per_host
            passes = num_io_ops < max_io_ops
            if passes:
                coefficient_vectors.append([0 for j in range(
                                                self.num_instances)])
            else:
                coefficient_vectors.append([1 for j in range(
                                                self.num_instances)])
                LOG.debug(_("%(host)s fails I/O ops check: Max IOs per host "
                            "is set to %(max_io_ops)s"),
                            {'host': host,
                             'max_io_ops': max_io_ops})

        return coefficient_vectors

    def get_variable_vectors(self, variables, hosts, instance_uuids,
                            request_spec, filter_properties):
        # The variable_vectors[i,j] denotes the relationship between
        # host[i] and instance[j].
        variable_vectors = []
        variable_vectors = [[variables[i][j] for j in range(
                        self.num_instances)] for i in range(self.num_hosts)]
        return variable_vectors

    def get_operations(self, variables, hosts, instance_uuids, request_spec,
                        filter_properties):
        # Operations are '=='.
        operations = [(lambda x: x == 0) for i in range(self.num_hosts)]
        return operations

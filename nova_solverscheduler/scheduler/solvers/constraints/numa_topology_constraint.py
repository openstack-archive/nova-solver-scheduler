# Copyright (c) 2015 Cisco Systems Inc.
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

import copy

from oslo_log import log as logging

from nova.scheduler.filters import numa_topology_filter
from nova_solverscheduler.scheduler.solvers import constraints

LOG = logging.getLogger(__name__)


class NUMATopologyConstraint(constraints.BaseLinearConstraint):
    """Constraint on requested NUMA topology."""

    def __init__(self):
        super(NUMATopologyConstraint, self).__init__()
        self.host_filter = numa_topology_filter.NUMATopologyFilter()

    def _get_acceptable_instance_num(self, host_state, filter_properties,
                                     max_num):
        instance = filter_properties['request_spec']['instance_properties']
        acceptable_num = 0
        while acceptable_num < max_num:
            if self.host_filter.host_passes(host_state, filter_properties):
                acceptable_num += 1
                host_state.consume_from_instance(instance)
            else:
                break
        return acceptable_num

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        for i in xrange(num_hosts):
            host_state = copy.deepcopy(hosts[i])
            acceptable_instance_num = self._get_acceptable_instance_num(
                    host_state, filter_properties, num_instances)

            if acceptable_instance_num < num_instances:
                inacceptable_num = num_instances - acceptable_instance_num
                constraint_matrix[i] = (
                        [True for j in xrange(acceptable_instance_num)] +
                        [False for j in xrange(inacceptable_num)])

            LOG.debug("%(host)s can accept %(num)s requested instances "
                        "according to NUMATopologyConstraint.",
                        {'host': hosts[i],
                        'num': acceptable_instance_num})

            numa_topology_limit = host_state.limits.get('numa_topology')
            if numa_topology_limit:
                hosts[i].limits['numa_topology'] = numa_topology_limit

        return constraint_matrix

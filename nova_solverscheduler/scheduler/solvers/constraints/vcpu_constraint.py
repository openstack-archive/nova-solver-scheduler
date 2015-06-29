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

from oslo_config import cfg
from oslo_log import log as logging

from nova.i18n import _LW
from nova_solverscheduler.scheduler.solvers import constraints

CONF = cfg.CONF
CONF.import_opt('cpu_allocation_ratio', 'nova.scheduler.filters.core_filter')

LOG = logging.getLogger(__name__)


class VcpuConstraint(constraints.BaseLinearConstraint):
    """Constraint of the total vcpu demand acceptable on each host."""

    def _get_cpu_allocation_ratio(self, host_state, filter_properties):
        return CONF.cpu_allocation_ratio

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        # get requested vcpus
        instance_type = filter_properties.get('instance_type') or {}
        if not instance_type:
            return constraint_matrix
        else:
            instance_vcpus = instance_type['vcpus']
        if instance_vcpus <= 0:
            LOG.warn(_LW("VcpuConstraint is skipped because requested "
                        "instance vCPU number is 0 or invalid."))
            return constraint_matrix

        for i in xrange(num_hosts):
            cpu_allocation_ratio = self._get_cpu_allocation_ratio(
                                                hosts[i], filter_properties)
            # get available vcpus
            if not hosts[i].vcpus_total:
                LOG.warn(_LW("vCPUs of %(host)s not set; assuming CPU "
                            "collection broken."), {'host': hosts[i]})
                continue
            else:
                vcpus_total = hosts[i].vcpus_total * cpu_allocation_ratio
                usable_vcpus = vcpus_total - hosts[i].vcpus_used

            acceptable_num_instances = int(usable_vcpus / instance_vcpus)
            if acceptable_num_instances < num_instances:
                inacceptable_num = num_instances - acceptable_num_instances
                constraint_matrix[i] = (
                        [True for j in xrange(acceptable_num_instances)] +
                        [False for j in xrange(inacceptable_num)])

            LOG.debug("%(host)s can accept %(num)s requested instances "
                        "according to VcpuConstraint.",
                        {'host': hosts[i],
                        'num': acceptable_num_instances})

            if vcpus_total > 0:
                hosts[i].limits['vcpu'] = vcpus_total

        return constraint_matrix

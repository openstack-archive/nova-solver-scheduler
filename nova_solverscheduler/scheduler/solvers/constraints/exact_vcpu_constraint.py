# Copyright (c) 2015 Cisco Systems, Inc.
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

from oslo_log import log as logging

from nova.i18n import _LW
from nova_solverscheduler.scheduler.solvers import constraints

LOG = logging.getLogger(__name__)


class ExactVcpuConstraint(constraints.BaseLinearConstraint):
    """Constraint that selects hosts with exact number of vCPUs."""

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
            LOG.warn(_LW("ExactVcpuConstraint is skipped because requested "
                         "instance vCPU number is 0 or invalid."))
            return constraint_matrix

        for i in xrange(num_hosts):
            # get available vcpus
            if not hosts[i].vcpus_total:
                LOG.warn(_LW("vCPUs of %(host)s not set; assuming CPU "
                             "collection broken."), {'host': hosts[i]})
                constraint_matrix[i] = [False for j in xrange(num_instances)]
                continue
            else:
                usable_vcpus = hosts[i].vcpus_total - hosts[i].vcpus_used

            if instance_vcpus == usable_vcpus:
                constraint_matrix[i] = (
                        [True] + [False for j in xrange(num_instances - 1)])
            else:
                constraint_matrix[i] = [False for j in xrange(num_instances)]
                LOG.debug("%(host)s does not have exactly %(requested_num)s "
                          "vcpus, it has %(usable_num)s vcpus.",
                          {'host': hosts[i],
                           'requested_num': instance_vcpus,
                           'usable_num': usable_vcpus})

        return constraint_matrix

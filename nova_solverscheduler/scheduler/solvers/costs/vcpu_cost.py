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

"""
VCPU Cost.  Calculate instance placement costs by hosts' vCPU usage.

The default is to spread instances across all hosts evenly.  If you prefer
stacking, you can set the 'vcpu_cost_multiplier' option to a negative
number and the cost has the opposite effect of the default.
"""

from oslo_config import cfg
from oslo_log import log as logging

from nova.i18n import _LW
from nova_solverscheduler.scheduler.solvers import costs as solver_costs
from nova_solverscheduler.scheduler.solvers.costs import utils

vcpu_cost_opts = [
        cfg.FloatOpt('vcpu_cost_multiplier',
                     default=1.0,
                     help='Multiplier used for vcpu costs. Negative '
                          'numbers mean to stack vs spread.'),
]

CONF = cfg.CONF
CONF.register_opts(vcpu_cost_opts, group='solver_scheduler')

LOG = logging.getLogger(__name__)


class VcpuCost(solver_costs.BaseLinearCost):

    def cost_multiplier(self):
        return CONF.solver_scheduler.vcpu_cost_multiplier

    def get_extended_cost_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        instance_type = filter_properties.get('instance_type') or {}
        requested_vcpus = instance_type.get('vcpus', 0)
        if requested_vcpus <= 0:
            LOG.warning(_LW("Requested instances\' vCPU number is 0 or invalid, "
                    "default value (0) is used."))

        remaining_vcpus_list = []
        for i in xrange(num_hosts):
            vcpus_total = hosts[i].vcpus_total
            vcpus_used = hosts[i].vcpus_used
            if not vcpus_total:
                LOG.warning(_LW("vCPUs of %(host)s not set; assuming CPU "
                            "collection broken."), {'host': hosts[i]})
                vcpus_total = 0
            remaining_vcpus = vcpus_total - vcpus_used
            remaining_vcpus_list.append(remaining_vcpus)

        extended_cost_matrix = [[0 for j in xrange(num_instances + 1)]
                                for i in xrange(num_hosts)]

        if requested_vcpus == 0:
            extended_cost_matrix = [
                    [(-remaining_vcpus_list[i])
                    for j in xrange(num_instances + 1)]
                    for i in xrange(num_hosts)]
        else:
            # we use int approximation here to avoid scaling problems after
            # normalization, in the case that the free vcpus in all hosts are
            # of very small values
            extended_cost_matrix = [
                    [-int(remaining_vcpus_list[i] / requested_vcpus) + j
                    for j in xrange(num_instances + 1)]
                    for i in xrange(num_hosts)]
        extended_cost_matrix = utils.normalize_cost_matrix(
                                                        extended_cost_matrix)
        return extended_cost_matrix

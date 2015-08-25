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

from oslo_config import cfg
from oslo_log import log as logging

from nova.i18n import _
from nova_solverscheduler.scheduler.solvers import constraints
from nova_solverscheduler.scheduler.solvers import utils as solver_utils

tenant_rack_opts = [
        cfg.IntOpt('max_racks_per_tenant',
                   default=1,
                   help='Maximum number of racks each tenant can have.'),
]

CONF = cfg.CONF
CONF.register_opts(tenant_rack_opts)

LOG = logging.getLogger(__name__)


def _get_sorted_racks(racks, hosts, host_racks_map, filter_properties):
    """sort racks by total acceptable instance nums, then avg costs."""

    def mixed_order(item):
        return (-item[1], item[2])

    num_hosts = len(hosts)
    num_instances = filter_properties.get('num_instances')

    solver_cache = filter_properties.get('solver_cache') or {}
    constraint_matrix = solver_cache.get('constraint_matrix', None)
    cost_matrix = solver_cache.get('cost_matrix', None)

    if not constraint_matrix:
        return list(racks)
    if not cost_matrix:
        cost_matrix = [[0 for j in xrange(num_instances)]
                        for i in xrange(num_hosts)]

    rack_avail_insts = {}
    rack_avg_costs = {}
    rack_num_hosts = {}
    rack_set = set([])

    for i in xrange(len(hosts)):
        host_name = hosts[i].host
        host_racks = host_racks_map.get(host_name, set())
        for rack in host_racks:
            if rack in racks:
                rack_set.add(rack)

                # get maximum available instances number for each rack
                cons = constraint_matrix[i]
                host_max_avail_insts = 0
                for j in xrange(len(cons)):
                    if cons[j] is True:
                        host_max_avail_insts = j + 1
                rack_avail_insts.setdefault(rack, 0)
                rack_avail_insts[rack] += host_max_avail_insts

                rack_num_hosts.setdefault(rack, 0)
                rack_num_hosts[rack] += 1

                rack_avg_costs.setdefault(rack, 0)
                n = rack_num_hosts[rack]
                rack_avg_costs[rack] = (rack_avg_costs[rack] * (n - 1) +
                                        cost_matrix[i][0]) / n

    rack_score_tuples = [
            (rack, rack_avail_insts[rack], rack_avg_costs[rack]) for
            rack in rack_set]

    sorted_rack_tuples = sorted(rack_score_tuples, key=mixed_order)
    sorted_racks = [rack for (rack, inst, cost) in sorted_rack_tuples]

    return sorted_racks


class TenantRackConstraint(constraints.BaseLinearConstraint):
    """Limit the maximum number of racks that instances of each tenant can
    spread across.
    If a host doesnot have rack config, it won't be filtered out by this
    constraint and will always be regarded as compatible with rack limit.
    """

    precedence = 1

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        max_racks = CONF.max_racks_per_tenant
        project_id = filter_properties['project_id']

        host_racks_map = solver_utils.get_host_racks_map(hosts)

        project_hosts = set([])
        project_racks = set([])
        other_racks = set([])

        for i in xrange(num_hosts):
            host_name = hosts[i].host
            host_racks = host_racks_map.get(host_name, set([]))
            if project_id in hosts[i].projects:
                project_racks = project_racks.union(host_racks)
                project_hosts.add(host_name)
            else:
                other_racks = other_racks.union(host_racks)
        other_racks = other_racks.difference(project_racks)

        additional_racks = []
        if len(project_racks) < max_racks:
            additional_rack_num = max_racks - len(project_racks)
            if additional_rack_num >= len(other_racks):
                additional_racks = list(other_racks)
            else:
                sorted_other_racks = _get_sorted_racks(
                        other_racks, hosts, host_racks_map, filter_properties)
                additional_racks = sorted_other_racks[0:additional_rack_num]

        acceptable_racks = project_racks.union(additional_racks)
        for i in xrange(num_hosts):
            host_name = hosts[i].host
            host_racks = host_racks_map.get(host_name, set([]))
            if (any([rack not in acceptable_racks for rack in host_racks])
                    and (host_name not in project_hosts)):
                constraint_matrix[i] = [False for j in xrange(num_instances)]

                LOG.debug(_("%(host)s cannot accept requested instances "
                        "according to TenantRackConstraint."),
                        {'host': host_name})
            else:
                LOG.debug(_("%(host)s can accept requested instances "
                        "according to TenantRackConstraint."),
                        {'host': host_name})

        return constraint_matrix

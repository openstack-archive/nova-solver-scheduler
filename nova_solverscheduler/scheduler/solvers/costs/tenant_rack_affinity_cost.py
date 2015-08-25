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
from nova_solverscheduler.scheduler.solvers import costs as solver_costs
from nova_solverscheduler.scheduler.solvers import utils as solver_utils

affinity_cost_opts = [
        cfg.FloatOpt('tenant_rack_affinity_cost_multiplier',
                     default=1.0,
                     help='Multiplier used for tenant rack affinity cost. '
                          'Must be a positive number.'),
]

CONF = cfg.CONF
CONF.register_opts(affinity_cost_opts, group='solver_scheduler')

LOG = logging.getLogger(__name__)


class TenantRackAffinityCost(solver_costs.BaseLinearCost):
    """Tenant Rack Affinity Cost tends to let scheduler place instances in
    the racks that contain existing instances of the tenant.
    If a rack has existing instances of the same tenant as that making request,
    then the hosts in the rack will have a lower cost value.
    """

    def __init__(self):
        super(TenantRackAffinityCost, self).__init__()

    def cost_multiplier(self):
        return CONF.solver_scheduler.tenant_rack_affinity_cost_multiplier

    def get_extended_cost_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        extended_cost_matrix = [[0 for j in xrange(num_instances + 1)]
                                for i in xrange(num_hosts)]

        project_id = filter_properties['project_id']

        host_racks_map = solver_utils.get_host_racks_map(hosts)

        affinity_racks = set([])
        affinity_hosts = set([])

        # get affinity racks/hosts
        for i in xrange(num_hosts):
            host_name = hosts[i].host
            host_racks = host_racks_map.get(host_name, set([]))
            if project_id in hosts[i].projects:
                affinity_hosts.add(host_name)
                affinity_racks = affinity_racks.union(host_racks)

        # check each hosts for affinity
        for i in xrange(num_hosts):
            host_name = hosts[i].host
            host_racks = host_racks_map.get(host_name, set([]))
            if (not any([rack in affinity_racks for rack in host_racks])) and (
                    host_name not in affinity_hosts):
                extended_cost_matrix[i] = [1 for j
                                            in xrange(num_instances + 1)]
            else:
                LOG.debug(_("%(host)s is in tenant affinity rack."),
                        {'host': host_name})

        return extended_cost_matrix

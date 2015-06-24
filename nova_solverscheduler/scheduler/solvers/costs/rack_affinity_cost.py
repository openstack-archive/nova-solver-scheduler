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

import six

from oslo.config import cfg

from nova import db
from nova.objects import instance as instance_obj
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova_solverscheduler.scheduler.solvers import costs as solver_costs
from nova_solverscheduler.scheduler.solvers import utils as solver_utils

affinity_cost_opts = [
        cfg.FloatOpt('tenant_rack_affinity_cost_multiplier',
                     default=1.0,
                     help='Multiplier used for tenant rack affinity cost. '
                          'Must be a positive number.'),
        cfg.FloatOpt('rack_network_affinity_cost_multiplier',
                     default=1.0,
                     help='Multiplier used for rack network affinity cost. '
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
        context = filter_properties['context']
        elevated = context.elevated()

        host_racks_map = db.aggregate_host_get_by_metadata_key(elevated,
                                                                key='rack')
        if not host_racks_map:
            # try load from external source
            host_racks_map = solver_utils.get_host_racks_config()

        affinity_racks = set([])
        affinity_hosts = set([])

        # get affinity racks/hosts
        for i in xrange(num_hosts):
            host_name = hosts[i].host
            host_racks = host_racks_map.get(host_name, set([]))

            # if tenant not in host state then tenant network does not exist
            # there, hence no need for further check
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


class RackNetworkAffinityCost(solver_costs.BaseLinearCost):
    """Rack Network Affinity Cost tends to let scheduler place instances in
    the racks that contain existing instances which are connected to the same
    tenant networks as requested instances.
    If a rack has existing instances that are connected to the same networks as
    those of requested instances, then the hosts in the rack will have a lower
    cost value.
    """

    def __init__(self):
        super(RackNetworkAffinityCost, self).__init__()

    def cost_multiplier(self):
        return CONF.solver_scheduler.rack_network_affinity_cost_multiplier

    def get_extended_cost_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        extended_cost_matrix = [[0 for j in xrange(num_instances + 1)]
                                for i in xrange(num_hosts)]

        project_id = filter_properties['project_id']
        context = filter_properties['context']
        elevated = context.elevated()
        scheduler_hints = filter_properties.get('scheduler_hints') or {}
        affinity_networks = scheduler_hints.get('affinity_networks', [])
        request_spec = filter_properties.get('request_spec', {})
        instance_properties = request_spec.get('instance_properties', {})
        requested_networks = request_spec.get('requested_networks', [])

        requested_net_ids = set([])
        # if a booting request, network ids are in request_spec
        # NOTE (Xinyuan): need to backport the following change,
        # Change-Id: I696a7ac1fe95e410d05e5fae1cccdbec39cba7ca
        for req_network in requested_networks:
            network_id = req_network.get('network_id', None)
            if network_id:
                requested_net_ids.add(network_id)
        # if the instance already exists, get network info from its info_cache
        instance_info_cache = instance_properties.get('info_cache', {})
        instance_network_info = instance_info_cache.get('network_info', [])
        for vif in instance_network_info:
            instance_network = vif.get('network', {})
            instance_network_id = instance_network.get('id', None)
            if instance_network_id:
                requested_net_ids.add(instance_network_id)
        # additional network ids from scheduler hint
        if isinstance(affinity_networks, six.string_types):
            affinity_networks = [affinity_networks]
        for affinity_network_id in affinity_networks:
            requested_net_ids.add(affinity_network_id)

        if not requested_net_ids:
            return extended_cost_matrix

        host_racks_map = db.aggregate_host_get_by_metadata_key(elevated,
                                                                key='rack')
        if not host_racks_map:
            # try load from external source
            host_racks_map = solver_utils.get_host_racks_config()

        affinity_racks = set([])
        affinity_hosts = set([])

        # get affinity racks/hosts
        for i in xrange(num_hosts):
            host_name = hosts[i].host
            host_racks = host_racks_map.get(host_name, set([]))

            # if tenant not in host state then tenant network does not exist
            # there, hence no need for further check
            if project_id not in hosts[i].projects:
                continue
            # if a host's racks already counted then no need to check the host
            if host_racks and host_racks.issubset(affinity_racks):
                continue

            instances = instance_obj.InstanceList.get_by_host(elevated,
                                    host_name, expected_attrs=['info_cache'])
            if not instances:
                continue

            for inst in instances:
                info_cache = inst.info_cache
                if info_cache is None:
                    continue
                network_info = info_cache.network_info or []
                instance_networks = [vif['network']['id']
                                    for vif in network_info]
                if requested_net_ids.intersection(instance_networks):
                    if not host_racks:
                        affinity_hosts.add(host_name)
                    else:
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
                LOG.debug(_("%(host)s is in network affinity rack."),
                        {'host': host_name})

        return extended_cost_matrix

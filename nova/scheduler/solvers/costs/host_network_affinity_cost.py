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

"""Host network cost."""

from nova.openstack.common import log as logging
from nova.scheduler.solvers import costs as solvercosts

from oslo.config import cfg

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class HostNetworkAffinityCost(solvercosts.BaseCost):
    """The cost is evaluated by the existence of
    requested networks in hosts.
    """

    def get_cost_matrix(self, hosts, instance_uuids, request_spec,
                        filter_properties):
        """Calculate the cost matrix."""
        num_hosts = len(hosts)
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)

        costs = [[0 for j in range(num_instances)]
                for i in range(num_hosts)]

        requested_networks = filter_properties.get('requested_networks', None)
        if requested_networks is None:
            return costs

        for i in range(num_hosts):
            host_cost = 0
            for network_id, requested_ip, port_id in requested_networks:
                if network_id:
                    if network_id in hosts[i].networks:
                        host_cost -= 1
            costs[i] = [host_cost for j in range(num_instances)]

        return costs

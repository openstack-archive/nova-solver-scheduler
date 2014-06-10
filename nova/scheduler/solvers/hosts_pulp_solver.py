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

"""
A reference solver implementation that models the scheduling problem as a
Linear Programming (LP) problem using the PULP modeling framework. This
implementation includes disk and memory constraints, and uses the free ram as
a cost metric to maximize or minimize for the LP problem.
"""

from oslo.config import cfg
from pulp import constants
from pulp import pulp

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler import solvers as novasolvers

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('disk_allocation_ratio', 'nova.scheduler.filters.disk_filter')
CONF.import_opt('ram_allocation_ratio', 'nova.scheduler.filters.ram_filter')
CONF.import_opt('ram_weight_multiplier', 'nova.scheduler.weights.ram')


class HostsPulpSolver(novasolvers.BaseHostSolver):
    """A LP based constraint solver implemented using PULP modeler."""

    def host_solve(self, hosts, instance_uuids, request_spec,
                   filter_properties):
        """This method returns a list of tuples - (host, instance_uuid)
           that are returned by the solver. Here the assumption is that
           all instance_uuids have the same requirement as specified in
           filter_properties
        """
        host_instance_tuples_list = []
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
            instance_uuids = ['unset_uuid%s' % i
                              for i in xrange(num_instances)]

        num_hosts = len(hosts)

        host_ids = ['Host%s' % i for i in range(num_hosts)]
        LOG.debug(_("All Hosts: %s") % [h.host for h in hosts])

        for host in hosts:
            LOG.debug(_("Host state: %s") % host)

        host_id_dict = dict(zip(host_ids, hosts))

        instances = ['Instance%s' % i for i in range(num_instances)]

        instance_id_dict = dict(zip(instances, instance_uuids))

        # supply is a dictionary for the number of units of
        # resource for each Host.
        # Currently using only the disk_mb and memory_mb
        # as the two resources to satisfy. Need to eventually be able to
        # plug-in different resources. An example supply dictionary:
        #        supply = {"Host1": [1000, 1000],
        #                  "Host2": [4000, 1000]}

        supply = dict((host_ids[i],
                       [self._get_usable_disk_mb(hosts[i]),
                        self._get_usable_memory_mb(hosts[i]), ])
                      for i in range(len(host_ids)))

        number_of_resource_types_per_host = 2

        required_disk_mb = self._get_required_disk_mb(filter_properties)
        required_memory_mb = self._get_required_memory_mb(filter_properties)

        # demand is a dictionary for the number of
        # units of resource required for each Instance.
        # An example demand dictionary:
        #         demand = {"Instance0":[200, 300],
        #                   "Instance1":[900, 100],
        #                   "Instance2":[1800, 200],
        #                   "Instance3":[200, 300],
        #                   "Instance4":[700, 800], }
        # However for the current scenario, all instances to be scheduled
        # per request have the same requirements. Need to eventually
        # to support requests to specify different instance requirements

        demand = dict((instances[i],
                       [required_disk_mb, required_memory_mb, ])
                      for i in range(num_instances))

        # Creates a list of costs of each Host-Instance assignment
        # Currently just like the nova.scheduler.weights.ram.RAMWeigher,
        # using host_state.free_ram_mb * ram_weight_multiplier
        # as the cost. A negative ram_weight_multiplier means to stack,
        # vs spread.
        # An example costs list:
        # costs = [  # Instances
        #          # 1 2 3 4 5
        #          [2, 4, 5, 2, 1],  # A   Hosts
        #          [3, 1, 3, 2, 3]  # B
        #          ]
        # Multiplying -1 as we want to use the same behavior of
        # ram_weight_multiplier as used by ram weigher.
        costs = [[-1 * host.free_ram_mb *
                  CONF.ram_weight_multiplier
                  for i in range(num_instances)]
                 for host in hosts]

        costs = pulp.makeDict([host_ids, instances], costs, 0)

        # The PULP LP problem variable used to add all the problem data
        prob = pulp.LpProblem("Host Instance Scheduler Problem",
                              constants.LpMinimize)

        all_host_instance_tuples = [(w, b)
                                    for w in host_ids
                                    for b in instances]

        vars = pulp.LpVariable.dicts("IA", (host_ids, instances),
                                     0, 1, constants.LpInteger)

        # The objective function is added to 'prob' first
        prob += (pulp.lpSum([vars[w][b] * costs[w][b]
                             for (w, b) in all_host_instance_tuples]),
                            "Sum_of_Host_Instance_Scheduling_Costs")

        # The supply maximum constraints are added to
        # prob for each supply node (Host)
        for w in host_ids:
            for i in range(number_of_resource_types_per_host):
                prob += (pulp.lpSum([vars[w][b] * demand[b][i]
                         for b in instances])
                        <= supply[w][i],
                        "Sum_of_Resource_%s" % i + "_provided_by_Host_%s" % w)

        # The number of Hosts required per Instance, in this case it is only 1
        for b in instances:
            prob += (pulp.lpSum([vars[w][b] for w in host_ids])
                     == 1, "Sum_of_Instance_Assignment%s" % b)

        # The demand minimum constraints are added to prob for
        # each demand node (Instance)
        for b in instances:
            for j in range(number_of_resource_types_per_host):
                prob += (pulp.lpSum([vars[w][b] * demand[b][j]
                                     for w in host_ids])
                         >= demand[b][j],
                    "Sum_of_Resource_%s" % j + "_required_by_Instance_%s" % b)

        # The problem is solved using PuLP's choice of Solver
        prob.solve()

        if pulp.LpStatus[prob.status] == 'Optimal':
            for v in prob.variables():
                if v.name.startswith('IA'):
                    (host_id, instance_id) = v.name.lstrip('IA').lstrip(
                                                         '_').split('_')
                    if v.varValue == 1.0:
                        host_instance_tuples_list.append(
                         (host_id_dict[host_id],
                          instance_id_dict[instance_id]))

        return host_instance_tuples_list

    def _get_usable_disk_mb(self, host_state):
        """This method returns the usable disk in mb for the given host.
         Takes into account the disk allocation ratio.
         (virtual disk to physical disk allocation ratio).
        """
        free_disk_mb = host_state.free_disk_mb
        total_usable_disk_mb = host_state.total_usable_disk_gb * 1024
        disk_allocation_ratio = CONF.disk_allocation_ratio
        disk_mb_limit = total_usable_disk_mb * disk_allocation_ratio
        used_disk_mb = total_usable_disk_mb - free_disk_mb
        usable_disk_mb = disk_mb_limit - used_disk_mb
        return usable_disk_mb

    def _get_required_disk_mb(self, filter_properties):
        """This method returns the required disk in mb from
         the given filter_properties dictionary object.
        """
        requested_disk_mb = 0
        instance_type = filter_properties.get('instance_type')
        if instance_type is not None:
            requested_disk_mb = 1024 * (instance_type.get('root_gb', 0) +
                                 instance_type.get('ephemeral_gb', 0))
        return requested_disk_mb

    def _get_usable_memory_mb(self, host_state):
        """This method returns the usable memory in mb for the given host.
         Takes into account the ram allocation ratio.
         (Virtual ram to physical ram allocation ratio).
        """
        free_ram_mb = host_state.free_ram_mb
        total_usable_ram_mb = host_state.total_usable_ram_mb
        ram_allocation_ratio = CONF.ram_allocation_ratio
        memory_mb_limit = total_usable_ram_mb * ram_allocation_ratio
        used_ram_mb = total_usable_ram_mb - free_ram_mb
        usable_ram_mb = memory_mb_limit - used_ram_mb
        return usable_ram_mb

    def _get_required_memory_mb(self, filter_properties):
        """This method returns the required memory in mb from
         the given filter_properties dictionary object
        """
        required_ram_mb = 0
        instance_type = filter_properties.get('instance_type')
        if instance_type is not None:
            required_ram_mb = instance_type.get('memory_mb', 0)
        return required_ram_mb

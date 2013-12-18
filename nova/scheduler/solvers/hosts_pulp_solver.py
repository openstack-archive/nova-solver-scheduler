# Copyright (c) 2012 OpenStack Foundation
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

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler import solvers as novasolvers
from pulp import *

LOG = logging.getLogger(__name__)

disk_allocation_ratio_opt = cfg.FloatOpt("disk_allocation_ratio", default=1.0,
    help="virtual disk to physical disk allocation ratio")

ram_allocation_ratio_opt = cfg.FloatOpt('ram_allocation_ratio',
    default=1.5,
    help='Virtual ram to physical ram allocation ratio which affects '
         'all ram filters. This configuration specifies a global ratio '
         'for RamFilter. For AggregateRamFilter, it will fall back to '
         'this configuration value if no per-aggregate setting found.')

ram_weight_opts = [
        cfg.FloatOpt('ram_optimization_cost_multiplier',
            default=1.0,
            help='Multiplier used for ram optimization cost metric. This '
                 'solver uses a LP minimization problem. So a negative '
                 'number would mean a cost maximization problem.'),
]

CONF = cfg.CONF
CONF.register_opt(ram_allocation_ratio_opt)
CONF.register_opt(disk_allocation_ratio_opt)
CONF.register_opts(ram_weight_opts)


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
        #Implement the solver logic here
        #------------------
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
            #Setting a unset uuid string for each instance
            instance_uuids = ['unset_uuid' + str(i)
                              for i in xrange(num_instances)]

        num_hosts = len(hosts)

        #A list of HostsIds
        Hosts = ['Host' + str(i) for i in range(num_hosts)]
        LOG.debug(_("All Hosts: %s") % [h.host for h in hosts])

        for host in hosts:
            LOG.debug(_("Host state: %s") % host)

        #A dictionary of Host Ids to host
        HostIdDict = dict(zip(Hosts, hosts))

        # Creating a list with some Instance ids for each instance required
        Instances = ['Instance' + str(i) for i in range(num_instances)]

        #A dictionary of Instance Ids to instance_uuids
        InstanceIdDict = dict(zip(Instances, instance_uuids))

        #        supply = {"Host1": [1000, 1000],
        #                  "Host2": [4000, 1000]}

        # Note(Yathi): Creates a dict for the number of units of
        # resource for each Host.
        # Currently using only the disk_mb and memory_mb
        # as the two resources to satisfy. Need to eventually be able to
        # plug-in different resources
        supply = {Hosts[i]: [self._get_usable_disk_mb(hosts[i]),
                             self._get_usable_memory_mb(hosts[i]), ]
                             for i in range(len(Hosts))}

        # The number of resource Types provided by the Host
        NumberOfResourceTypesPerHost = 2

        #         demand = {"Instance0":[200, 300],
        #                   "Instance1":[900, 100],
        #                   "Instance2":[1800, 200],
        #                   "Instance3":[200, 300],
        #                   "Instance4":[700, 800], }

        required_disk_mb = self._get_required_disk_mb(filter_properties)
        required_memory_mb = self._get_required_memory_mb(filter_properties)
        # Creates a dictionary for the number of
        # units of resource for each Instance
        demand = {Instances[i]: [required_disk_mb, required_memory_mb, ]
                  for i in range(num_instances)}

        # costs = [  # Instances
        #          # 1 2 3 4 5
        #          [2, 4, 5, 2, 1],  # A   Hosts
        #          [3, 1, 3, 2, 3]  # B
        #          ]

        # Creates a list of costs of each Host-Instance assignment
        # Currently just like the nova.scheduler.weights.ram.RAMWeigher,
        # using host_state.free_ram_mb * CONF.ram_optimization_cost_multiplier
        # as the cost
        # TODO(Yathi) add pluggable costs matrix according to
        # different resource types costs
        costs = [[host.free_ram_mb * CONF.ram_weight_multiplier
                  for i in range(num_instances)] for host in hosts]

        # The cost data is made into a dictionary
        costs = makeDict([Hosts, Instances], costs, 0)

        # Creates the 'prob' variable to contain the problem data
        prob = LpProblem("Host Instance Scheduler Problem", LpMinimize)

        # Creates a list of tuples containing all
        # the possible HostInstanceTuples
        AllHostInstanceTuples = [(w, b) for w in Hosts for b in Instances]

        # A dictionary called 'Vars' is created to contain the
        # referenced variables(the AllHostInstanceTuples)
        vars = LpVariable.dicts("IA", (Hosts, Instances), 0, 1, LpInteger)

        # The objective function is added to 'prob' first
        prob += (lpSum([
                       vars[w][b] * costs[w][b]
                       for (w, b) in AllHostInstanceTuples
                       ]), "Sum_of_Host_Instance_Scheduling_Costs")

        # The supply maximum constraints are added to
        # prob for each supply node (Host)
        for w in Hosts:
            for i in range(NumberOfResourceTypesPerHost):
                prob += (lpSum([vars[w][b] * demand[b][i] for b in Instances])
                        <= supply[w][i],
                        "Sum_of_Resource_%s" % i + "_provided_by_Host_%s" % w)

        # The number of Hosts required per Instance, in this case it is only 1
        for b in Instances:
            prob += (lpSum([vars[w][b] for w in Hosts])
                     == 1, "Sum_of_Instance_Assignment%s" % b)

        # The demand minimum constraints are added to prob for
        # each demand node (Instance)
        for b in Instances:
            for j in range(NumberOfResourceTypesPerHost):
                prob += (lpSum([vars[w][b] * demand[b][j]
                                for w in Hosts])
                         >= demand[b][j],
                    "Sum_of_Resource_%s" % j + "_required_by_Instance_%s" % b)

        # The problem data is written to an .lp file
        prob.writeLP("HostsPulpSolver.lp")

        # The problem is solved using PuLP's choice of Solver
        prob.solve()

        if LpStatus[prob.status] == 'Optimal':
            for v in prob.variables():
                if v.name.startswith('IA'):
                    (hostId, instanceId) = v.name.lstrip('IA').lstrip(
                                                         '_').split('_')
                    if v.varValue == 1.0:
                        host_instance_tuples_list.append((HostIdDict[hostId],
                                                InstanceIdDict[instanceId]))

        return host_instance_tuples_list

    def _get_usable_disk_mb(self, host_state):
        """This method returns the usable disk in mb for the given host.
         Takes into account the disk allocation ratio.
         (virtual disk to physical disk allocation ratio).
        """
        free_disk_mb = host_state.free_disk_mb
        total_usable_disk_mb = host_state.total_usable_disk_gb * 1024
        disk_mb_limit = total_usable_disk_mb * CONF.disk_allocation_ratio
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

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

from pulp import constants
from pulp import pulp

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler import solvers as scheduler_solver

LOG = logging.getLogger(__name__)


class HostsPulpSolver(scheduler_solver.BaseHostSolver):
    """A LP based pluggable LP solver implemented using PULP modeler."""

    def __init__(self):
        self.cost_classes = self._get_cost_classes()
        self.constraint_classes = self._get_constraint_classes()
        self.cost_weights = self._get_cost_weights()

    def host_solve(self, hosts, instance_uuids, request_spec,
                    filter_properties):
        """This method returns a list of tuples - (host, instance_uuid)
        that are returned by the solver. Here the assumption is that
        all instance_uuids have the same requirement as specified in
        filter_properties.
        """
        host_instance_tuples_list = []

        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
            #Setting a unset uuid string for each instance.
            instance_uuids = ['unset_uuid' + str(i)
                                for i in xrange(num_instances)]

        num_hosts = len(hosts)

        LOG.debug(_("All Hosts: %s") % [h.host for h in hosts])
        for host in hosts:
            LOG.debug(_("Host state: %s") % host)

        # Create dictionaries mapping host/instance IDs to hosts/instances.
        host_ids = ['Host' + str(i) for i in range(num_hosts)]
        host_id_dict = dict(zip(host_ids, hosts))
        instance_ids = ['Instance' + str(i) for i in range(num_instances)]
        instance_id_dict = dict(zip(instance_ids, instance_uuids))

        # Create the 'prob' variable to contain the problem data.
        prob = pulp.LpProblem("Host Instance Scheduler Problem",
                                constants.LpMinimize)

        # Create the 'variables' matrix to contain the referenced variables.
        variables = [[pulp.LpVariable("IA" + "_Host" + str(i) + "_Instance" +
                    str(j), 0, 1, constants.LpInteger) for j in
                    range(num_instances)] for i in range(num_hosts)]

        # Get costs and constraints and formulate the linear problem.
        self.cost_objects = [cost() for cost in self.cost_classes]
        self.constraint_objects = [constraint(variables, hosts,
                            instance_uuids, request_spec, filter_properties)
                            for constraint in self.constraint_classes]

        costs = [[0 for j in range(num_instances)] for i in range(num_hosts)]
        for cost_object in self.cost_objects:
            cost = cost_object.get_cost_matrix(hosts, instance_uuids,
                                            request_spec, filter_properties)
            cost = cost_object.normalize_cost_matrix(cost, 0.0, 1.0)
            weight = float(self.cost_weights[cost_object.__class__.__name__])
            costs = [[costs[i][j] + weight * cost[i][j]
                    for j in range(num_instances)] for i in range(num_hosts)]
        prob += (pulp.lpSum([costs[i][j] * variables[i][j]
                    for i in range(num_hosts) for j in range(num_instances)]),
                    "Sum_of_Host_Instance_Scheduling_Costs")

        for constraint_object in self.constraint_objects:
            coefficient_vectors = constraint_object.get_coefficient_vectors(
                                            variables, hosts, instance_uuids,
                                            request_spec, filter_properties)
            variable_vectors = constraint_object.get_variable_vectors(
                                            variables, hosts, instance_uuids,
                                            request_spec, filter_properties)
            operations = constraint_object.get_operations(
                                            variables, hosts, instance_uuids,
                                            request_spec, filter_properties)
            for i in range(len(operations)):
                operation = operations[i]
                len_vector = len(variable_vectors[i])
                prob += (operation(pulp.lpSum([coefficient_vectors[i][j]
                    * variable_vectors[i][j] for j in range(len_vector)])),
                    "Costraint_Name_%s" % constraint_object.__class__.__name__
                    + "_No._%s" % i)

        # The problem is solved using PULP's choice of Solver.
        prob.solve()

        # Create host-instance tuples from the solutions.
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

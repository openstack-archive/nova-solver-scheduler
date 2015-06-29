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
from pulp import solvers as pulp_solver_classes

from oslo_config import cfg
from oslo_log import log as logging

from nova.i18n import _LW
from nova_solverscheduler.scheduler import solvers as scheduler_solver

pulp_solver_opts = [
        cfg.IntOpt('pulp_solver_timeout_seconds',
                    default=20,
                    help='How much time in seconds is allowed for solvers to '
                         'solve the scheduling problem. If this time limit '
                         'is exceeded the solver will be stopped.'),
]

CONF = cfg.CONF
CONF.register_opts(pulp_solver_opts, group='solver_scheduler')

LOG = logging.getLogger(__name__)


class PulpSolver(scheduler_solver.BaseHostSolver):
    """A LP based pluggable LP solver implemented using PULP modeler."""

    def __init__(self):
        super(PulpSolver, self).__init__()
        self.cost_classes = self._get_cost_classes()
        self.constraint_classes = self._get_constraint_classes()

    def _get_cost_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances', 1)
        solver_cache = filter_properties['solver_cache']
        # initialize cost matrix
        cost_matrix = [[0 for j in xrange(num_instances + 1)]
                        for i in xrange(num_hosts)]
        solver_cache['cost_matrix'] = cost_matrix
        cost_objects = [cost() for cost in self.cost_classes]
        cost_objects.sort(key=lambda cost: cost.precedence)
        precedence_level = 0
        for cost_object in cost_objects:
            if cost_object.precedence > precedence_level:
                # update cost matrix in the solver cache
                solver_cache['cost_matrix'] = cost_matrix
                precedence_level = cost_object.precedence
            cost_multiplier = cost_object.cost_multiplier()
            this_cost_mat = cost_object.get_extended_cost_matrix(hosts,
                                                        filter_properties)
            if not this_cost_mat:
                continue
            cost_matrix = [[cost_matrix[i][j] +
                    this_cost_mat[i][j] * cost_multiplier
                    for j in xrange(num_instances + 1)]
                    for i in xrange(num_hosts)]
        # update cost matrix in the solver cache
        solver_cache['cost_matrix'] = cost_matrix

        return cost_matrix

    def _get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances', 1)
        solver_cache = filter_properties['solver_cache']
        # initialize constraint_matrix
        constraint_matrix = [[True for j in xrange(num_instances + 1)]
                            for i in xrange(num_hosts)]
        solver_cache['constraint_matrix'] = constraint_matrix
        constraint_objects = [cons() for cons in self.constraint_classes]
        constraint_objects.sort(key=lambda cons: cons.precedence)
        precedence_level = 0
        for constraint_object in constraint_objects:
            if constraint_object.precedence > precedence_level:
                # update constraint matrix in the solver cache
                solver_cache['constraint_matrix'] = constraint_matrix
                precedence_level = constraint_object.precedence
            this_cons_mat = constraint_object.get_constraint_matrix(hosts,
                                                        filter_properties)
            if not this_cons_mat:
                continue
            for i in xrange(num_hosts):
                constraint_matrix[i][1:] = [constraint_matrix[i][j + 1] &
                        this_cons_mat[i][j] for j in xrange(num_instances)]
        # update constraint matrix in the solver cache
        solver_cache['constraint_matrix'] = constraint_matrix

        return constraint_matrix

    def _adjust_cost_matrix(self, cost_matrix):
        """Modify cost matrix to fit the optimization problem."""
        new_cost_matrix = cost_matrix
        if not cost_matrix:
            return new_cost_matrix
        first_column = [row[0] for row in cost_matrix]
        last_column = [row[-1] for row in cost_matrix]
        if sum(first_column) < sum(last_column):
            offset = min(first_column)
            sign = 1
        else:
            offset = max(first_column)
            sign = -1
        for i in xrange(len(cost_matrix)):
            for j in xrange(len(cost_matrix[i])):
                new_cost_matrix[i][j] = sign * (
                                        (cost_matrix[i][j] - offset) ** 2)
        return new_cost_matrix

    def solve(self, hosts, filter_properties):
        """This method returns a list of tuples - (host, instance_uuid)
        that are returned by the solver. Here the assumption is that
        all instance_uuids have the same requirement as specified in
        filter_properties.
        """
        host_instance_combinations = []

        num_instances = filter_properties['num_instances']
        num_hosts = len(hosts)

        instance_uuids = filter_properties.get('instance_uuids') or [
                '(unknown_uuid)' + str(i) for i in xrange(num_instances)]

        filter_properties.setdefault('solver_cache', {})
        filter_properties['solver_cache'].update(
                {'cost_matrix': [],
                'constraint_matrix': []})

        cost_matrix = self._get_cost_matrix(hosts, filter_properties)
        cost_matrix = self._adjust_cost_matrix(cost_matrix)
        constraint_matrix = self._get_constraint_matrix(hosts,
                                                        filter_properties)

        # Create dictionaries mapping temporary host/instance keys to
        # hosts/instance_uuids. These temorary keys are to be used in the
        # solving process since we need a convention of lp variable names.
        host_keys = ['Host' + str(i) for i in xrange(num_hosts)]
        host_key_map = dict(zip(host_keys, hosts))
        instance_num_keys = ['InstanceNum' + str(i) for
                            i in xrange(num_instances + 1)]
        instance_num_key_map = dict(zip(instance_num_keys,
                                        xrange(num_instances + 1)))

        # create the pulp variables
        variable_matrix = [
                [pulp.LpVariable('HI_' + host_key + '_' + instance_num_key,
                0, 1, constants.LpInteger)
                for instance_num_key in instance_num_keys]
                for host_key in host_keys]

        # create the 'prob' variable to contain the problem data.
        prob = pulp.LpProblem("Host Instance Scheduler Problem",
                                constants.LpMinimize)

        # add cost function to pulp solver
        cost_variables = [variable_matrix[i][j] for i in xrange(num_hosts)
                                        for j in xrange(num_instances + 1)]
        cost_coefficients = [cost_matrix[i][j] for i in xrange(num_hosts)
                                        for j in xrange(num_instances + 1)]
        prob += (pulp.lpSum([cost_coefficients[i] * cost_variables[i]
                for i in xrange(len(cost_variables))]), "Sum_Costs")

        # add constraints to pulp solver
        for i in xrange(num_hosts):
            for j in xrange(num_instances + 1):
                if constraint_matrix[i][j] is False:
                    prob += (variable_matrix[i][j] == 0,
                            "Cons_Host_%s" % i + "_NumInst_%s" % j)

        # add additional constraints to ensure the problem is valid
        # (1) non-trivial solution: number of all instances == that requested
        prob += (pulp.lpSum([variable_matrix[i][j] * j for i in
                xrange(num_hosts) for j in xrange(num_instances + 1)]) ==
                num_instances, "NonTrivialCons")
        # (2) valid solution: each host is assigned 1 num-instances value
        for i in xrange(num_hosts):
            prob += (pulp.lpSum([variable_matrix[i][j] for j in
                    xrange(num_instances + 1)]) == 1, "ValidCons_Host_%s" % i)

        # The problem is solved using PULP's choice of Solver.
        prob.solve(pulp_solver_classes.PULP_CBC_CMD(
                maxSeconds=CONF.solver_scheduler.pulp_solver_timeout_seconds))

        # Create host-instance tuples from the solutions.
        if pulp.LpStatus[prob.status] == 'Optimal':
            num_insts_on_host = {}
            for v in prob.variables():
                if v.name.startswith('HI'):
                    (host_key, instance_num_key) = v.name.lstrip('HI').lstrip(
                                                        '_').split('_')
                    if v.varValue == 1:
                        num_insts_on_host[host_key] = (
                                        instance_num_key_map[instance_num_key])
            instances_iter = iter(instance_uuids)
            for host_key in host_keys:
                num_insts_on_this_host = num_insts_on_host.get(host_key, 0)
                for i in xrange(num_insts_on_this_host):
                    host_instance_combinations.append(
                            (host_key_map[host_key], instances_iter.next()))
        else:
            LOG.warn(_LW("Pulp solver didnot find optimal solution! "
                    "reason: %s"), pulp.LpStatus[prob.status])
            host_instance_combinations = []

        return host_instance_combinations

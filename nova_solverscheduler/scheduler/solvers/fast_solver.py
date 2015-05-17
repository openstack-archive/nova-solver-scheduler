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

import operator

from nova_solverscheduler.scheduler import solvers as scheduler_solver


class FastSolver(scheduler_solver.BaseHostSolver):

    def __init__(self):
        super(FastSolver, self).__init__()
        self.cost_classes = self._get_cost_classes()
        self.constraint_classes = self._get_constraint_classes()

    def _get_cost_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances', 1)
        solver_cache = filter_properties['solver_cache']
        # initialize cost matrix
        cost_matrix = [[0 for j in xrange(num_instances)]
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
            this_cost_mat = cost_object.get_cost_matrix(hosts,
                                                        filter_properties)
            if not this_cost_mat:
                continue
            cost_matrix = [[cost_matrix[i][j] +
                    this_cost_mat[i][j] * cost_multiplier
                    for j in xrange(num_instances)]
                    for i in xrange(num_hosts)]
        # update cost matrix in the solver cache
        solver_cache['cost_matrix'] = cost_matrix

        return cost_matrix

    def _get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances', 1)
        solver_cache = filter_properties['solver_cache']
        # initialize constraint_matrix
        constraint_matrix = [[True for j in xrange(num_instances)]
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
            constraint_matrix = [[constraint_matrix[i][j] &
                    this_cons_mat[i][j] for j in xrange(num_instances)]
                    for i in xrange(num_hosts)]
        # update constraint matrix in the solver cache
        solver_cache['constraint_matrix'] = constraint_matrix

        return constraint_matrix

    def solve(self, hosts, filter_properties):
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
        constraint_matrix = self._get_constraint_matrix(hosts,
                                                        filter_properties)

        placement_cost_tuples = []
        for i in xrange(num_hosts):
            for j in xrange(num_instances):
                if constraint_matrix[i][j]:
                    host_idx = i
                    inst_num = j + 1
                    cost_val = cost_matrix[i][j]
                    placement_cost_tuples.append(
                                            (host_idx, inst_num, cost_val))

        sorted_placement_costs = sorted(placement_cost_tuples,
                                        key=operator.itemgetter(2))

        host_inst_alloc = [0 for i in xrange(num_hosts)]
        allocated_inst_num = 0
        for (host_idx, inst_num, cost_val) in sorted_placement_costs:
            delta = inst_num - host_inst_alloc[host_idx]

            if (delta <= 0) or (allocated_inst_num + delta > num_instances):
                continue

            host_inst_alloc[host_idx] += delta
            allocated_inst_num += delta

            if allocated_inst_num == num_instances:
                break

        instances_iter = iter(instance_uuids)
        for i in xrange(len(host_inst_alloc)):
            num = host_inst_alloc[i]
            for n in xrange(num):
                host_instance_combinations.append(
                                            (hosts[i], instances_iter.next()))

        return host_instance_combinations

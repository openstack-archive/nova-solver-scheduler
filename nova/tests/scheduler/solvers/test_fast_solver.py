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

import mock

from nova.scheduler import solver_scheduler_host_manager as host_manager
from nova.scheduler.solvers import constraints
from nova.scheduler.solvers import costs
from nova.scheduler.solvers import fast_solver
from nova import test


class FakeCost1(costs.BaseLinearCost):
    def cost_multiplier(self):
        return 1

    def get_cost_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances', 1)
        cost_matrix = [[i for j in xrange(num_instances)]
                                                for i in xrange(num_hosts)]
        return cost_matrix


class FakeCost2(costs.BaseLinearCost):
    precedence = 1

    def cost_multiplier(self):
        return 2

    def get_cost_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances', 1)
        m = filter_properties['solver_cache']['cost_matrix']
        cost_matrix = [[-m[i][j] for j in xrange(num_instances)]
                                                for i in xrange(num_hosts)]
        return cost_matrix


class FakeConstraint1(constraints.BaseLinearConstraint):
    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances', 1)
        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]
        constraint_matrix[0] = [False for j in xrange(num_instances)]
        return constraint_matrix


class FakeConstraint2(constraints.BaseLinearConstraint):
    precedence = 1

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances', 1)
        m = filter_properties['solver_cache']['constraint_matrix']
        if m[0][0] is False:
            constraint_matrix = [[True for j in xrange(num_instances)]
                                for i in xrange(num_hosts)]
            constraint_matrix[-1] = [False for j in xrange(num_instances)]
        else:
            constraint_matrix = [[False for j in xrange(num_instances)]
                                for i in xrange(num_hosts)]
        return constraint_matrix


class TestGetMatrix(test.NoDBTestCase):

    def setUp(self):
        super(TestGetMatrix, self).setUp()
        self.fast_solver = fast_solver.FastSolver()
        self.fake_hosts = [host_manager.SolverSchedulerHostState(
                'fake_host%s' % x, 'fake-node') for x in xrange(1, 5)]
        self.fake_hosts += [host_manager.SolverSchedulerHostState(
                'fake_multihost', 'fake-node%s' % x) for x in xrange(1, 5)]

    def test_get_cost_matrix_one_cost(self):
        self.fast_solver.cost_classes = [FakeCost1]
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }
        expected_cost_mat = [
            [0, 0, 0],
            [1, 1, 1],
            [2, 2, 2],
            [3, 3, 3]]
        cost_mat = self.fast_solver._get_cost_matrix(hosts, filter_properties)
        self.assertEqual(expected_cost_mat, cost_mat)
        cost_mat_cache = filter_properties['solver_cache']['cost_matrix']
        self.assertEqual(expected_cost_mat, cost_mat_cache)

    def test_get_cost_matrix_multi_cost(self):
        self.fast_solver.cost_classes = [FakeCost1, FakeCost2]
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }
        expected_cost_mat = [
            [-0, -0, -0],
            [-1, -1, -1],
            [-2, -2, -2],
            [-3, -3, -3]]
        cost_mat = self.fast_solver._get_cost_matrix(hosts, filter_properties)
        self.assertEqual(expected_cost_mat, cost_mat)
        cost_mat_cache = filter_properties['solver_cache']['cost_matrix']
        self.assertEqual(expected_cost_mat, cost_mat_cache)

    def test_get_cost_matrix_multi_cost_change_order(self):
        self.fast_solver.cost_classes = [FakeCost2, FakeCost1]
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }
        expected_cost_mat = [
            [-0, -0, -0],
            [-1, -1, -1],
            [-2, -2, -2],
            [-3, -3, -3]]
        cost_mat = self.fast_solver._get_cost_matrix(hosts, filter_properties)
        self.assertEqual(expected_cost_mat, cost_mat)
        cost_mat_cache = filter_properties['solver_cache']['cost_matrix']
        self.assertEqual(expected_cost_mat, cost_mat_cache)

    def test_get_constraint_matrix_one_constraint(self):
        self.fast_solver.constraint_classes = [FakeConstraint1]
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }
        expected_cons_mat = [
            [False, False, False],
            [True, True, True],
            [True, True, True],
            [True, True, True]]
        cons_mat = self.fast_solver._get_constraint_matrix(hosts,
                                                            filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)
        cons_mat_cache = filter_properties['solver_cache'][
                                                        'constraint_matrix']
        self.assertEqual(expected_cons_mat, cons_mat_cache)

    def test_get_constraint_matrix_multi_constraint(self):
        self.fast_solver.constraint_classes = [FakeConstraint1,
                                                FakeConstraint2]
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }
        expected_cons_mat = [
            [False, False, False],
            [True, True, True],
            [True, True, True],
            [False, False, False]]
        cons_mat = self.fast_solver._get_constraint_matrix(hosts,
                                                            filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)
        cons_mat_cache = filter_properties['solver_cache'][
                                                        'constraint_matrix']
        self.assertEqual(expected_cons_mat, cons_mat_cache)

    def test_get_constraint_matrix_multi_constraint_change_order(self):
        self.fast_solver.constraint_classes = [FakeConstraint2,
                                                FakeConstraint1]
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }
        expected_cons_mat = [
            [False, False, False],
            [True, True, True],
            [True, True, True],
            [False, False, False]]
        cons_mat = self.fast_solver._get_constraint_matrix(hosts,
                                                            filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)
        cons_mat_cache = filter_properties['solver_cache'][
                                                        'constraint_matrix']
        self.assertEqual(expected_cons_mat, cons_mat_cache)


@mock.patch.object(fast_solver.FastSolver, '_get_constraint_matrix')
@mock.patch.object(fast_solver.FastSolver, '_get_cost_matrix')
class TestFastSolver(test.NoDBTestCase):

    def setUp(self):
        super(TestFastSolver, self).setUp()
        self.fast_solver = fast_solver.FastSolver()
        self.fake_hosts = [host_manager.SolverSchedulerHostState(
                'fake_host%s' % x, 'fake-node') for x in xrange(1, 5)]
        self.fake_hosts += [host_manager.SolverSchedulerHostState(
                'fake_multihost', 'fake-node%s' % x) for x in xrange(1, 5)]

    def test_spreading_cost(self, get_costmat, get_consmat):
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }

        # cost matrix:
        # [[0, 1, 2],
        #  [1, 2, 3],
        #  [2, 3, 4],
        #  [3, 4, 5]]
        get_costmat.return_value = [[j + i for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]
        # constraint matrix:
        # [[True, True, True],
        #  [True, True, True],
        #  [True, True, True],
        #  [True, True, True]]
        get_consmat.return_value = [[True for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]

        expected_result = [
            (hosts[0], 'fake_uuid_0'),
            (hosts[0], 'fake_uuid_1'),
            (hosts[1], 'fake_uuid_2')]

        result = self.fast_solver.solve(hosts, filter_properties)
        self.assertEqual(expected_result, result)

    def test_spreading_cost_with_constraint(self, get_costmat, get_consmat):
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }

        # cost matrix:
        # [[0, 1, 2],
        #  [1, 2, 3],
        #  [2, 3, 4],
        #  [3, 4, 5]]
        get_costmat.return_value = [[j + i for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]
        # constraint matrix:
        # [[False, False, False],
        #  [True, False, False],
        #  [True, True, True],
        #  [True, True, True]]
        get_consmat.return_value = [
            [False, False, False],
            [True, False, False],
            [True, True, True],
            [True, True, True]]

        expected_result = [
            (hosts[1], 'fake_uuid_0'),
            (hosts[2], 'fake_uuid_1'),
            (hosts[2], 'fake_uuid_2')]

        result = self.fast_solver.solve(hosts, filter_properties)
        self.assertEqual(expected_result, result)

    def test_stacking_cost(self, get_costmat, get_consmat):
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }

        # cost matrix:
        # [[-0, -1, -2],
        #  [-1, -2, -3],
        #  [-2, -3, -4],
        #  [-3, -4, -5]]
        get_costmat.return_value = [[-(j + i) for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]
        # constraint matrix:
        # [[True, True, True],
        #  [True, True, True],
        #  [True, True, True],
        #  [True, True, True]]
        get_consmat.return_value = [[True for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]

        expected_result = [
            (hosts[3], 'fake_uuid_0'),
            (hosts[3], 'fake_uuid_1'),
            (hosts[3], 'fake_uuid_2')]

        result = self.fast_solver.solve(hosts, filter_properties)
        self.assertEqual(expected_result, result)

    def test_stacking_cost_with_constraint(self, get_costmat, get_consmat):
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }

        # cost matrix:
        # [[-0, -1, -2],
        #  [-1, -2, -3],
        #  [-2, -3, -4],
        #  [-3, -4, -5]]
        get_costmat.return_value = [[-(j + i) for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]
        # constraint matrix:
        # [[True, True, True],
        #  [True, True, True],
        #  [True, True, True],
        #  [True, False, False]]
        get_consmat.return_value = [
            [True, True, True],
            [True, True, True],
            [True, True, True],
            [True, False, False]]

        expected_result = [
            (hosts[2], 'fake_uuid_0'),
            (hosts[2], 'fake_uuid_1'),
            (hosts[2], 'fake_uuid_2')]

        result = self.fast_solver.solve(hosts, filter_properties)
        self.assertEqual(expected_result, result)

    def test_constant_cost(self, get_costmat, get_consmat):
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }

        # cost matrix:
        # [[0, 0, 0],
        #  [1, 1, 1],
        #  [2, 2, 2],
        #  [3, 3, 3]]
        get_costmat.return_value = [[i for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]
        # constraint matrix:
        # [[True, True, True],
        #  [True, True, True],
        #  [True, True, True],
        #  [True, True, True]]
        get_consmat.return_value = [[True for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]

        expected_result = [
            (hosts[0], 'fake_uuid_0'),
            (hosts[0], 'fake_uuid_1'),
            (hosts[0], 'fake_uuid_2')]

        result = self.fast_solver.solve(hosts, filter_properties)
        self.assertEqual(expected_result, result)

    def test_constant_cost_with_constraint(self, get_costmat, get_consmat):
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }

        # cost matrix:
        # [[0, 0, 0],
        #  [1, 1, 1],
        #  [2, 2, 2],
        #  [3, 3, 3]]
        get_costmat.return_value = [[i for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]
        # constraint matrix:
        # [[False, False, False],
        #  [True, False, False],
        #  [True, True, False],
        #  [True, True, True]]
        get_consmat.return_value = [
            [False, False, False],
            [True, False, False],
            [True, True, False],
            [True, True, True]]

        expected_result = [
            (hosts[1], 'fake_uuid_0'),
            (hosts[2], 'fake_uuid_1'),
            (hosts[2], 'fake_uuid_2')]

        result = self.fast_solver.solve(hosts, filter_properties)
        self.assertEqual(expected_result, result)

    def test_no_cost_no_constraint(self, get_costmat, get_consmat):
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }

        # cost matrix:
        # [[0, 0, 0],
        #  [0, 0, 0],
        #  [0, 0, 0],
        #  [0, 0, 0]]
        get_costmat.return_value = [[0 for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]
        # constraint matrix:
        # [[True, True, True],
        #  [True, True, True],
        #  [True, True, True],
        #  [True, True, True]]
        get_consmat.return_value = [[True for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]

        expected_result = [
            (hosts[0], 'fake_uuid_0'),
            (hosts[0], 'fake_uuid_1'),
            (hosts[0], 'fake_uuid_2')]

        result = self.fast_solver.solve(hosts, filter_properties)
        self.assertEqual(expected_result, result)

    def test_no_valid_solution(self, get_costmat, get_consmat):
        num_hosts = 4
        num_insts = 3
        hosts = self.fake_hosts[0:num_hosts]
        filter_properties = {
            'num_instances': num_insts,
            'instance_uuids': ['fake_uuid_%s' % x for x in xrange(num_insts)],
            'solver_cache': {}
        }

        # cost matrix:
        # [[0, 0, 0],
        #  [1, 1, 1],
        #  [2, 2, 2],
        #  [3, 3, 3]]
        get_costmat.return_value = [[i for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]
        # constraint matrix:
        # [[False, False, False],
        #  [False, False, False],
        #  [False, False, False],
        #  [False, False, False]]
        get_consmat.return_value = [[False for j in xrange(num_insts)]
                                    for i in xrange(num_hosts)]

        expected_result = []

        result = self.fast_solver.solve(hosts, filter_properties)
        self.assertEqual(expected_result, result)

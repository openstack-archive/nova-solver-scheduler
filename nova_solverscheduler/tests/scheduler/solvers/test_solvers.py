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

import mock

from nova import test
from nova_solverscheduler.scheduler import solvers
from nova_solverscheduler.scheduler.solvers import constraints
from nova_solverscheduler.scheduler.solvers import costs
from nova_solverscheduler import solver_scheduler_exception as exception


class FakeCost1(costs.BaseCost):
    def get_components(self, variables, hosts, filter_properties):
        pass


class FakeCost2(costs.BaseCost):
    def get_components(self, variables, hosts, filter_properties):
        pass


class FakeConstraint1(constraints.BaseConstraint):
    def get_components(self, variables, hosts, filter_properties):
        pass


class FakeConstraint2(constraints.BaseConstraint):
    def get_components(self, variables, hosts, filter_properties):
        pass


class TestBaseHostSolver(test.NoDBTestCase):
    """Test case for scheduler base solver."""

    def setUp(self):
        super(TestBaseHostSolver, self).setUp()
        self.solver = solvers.BaseHostSolver()

    @mock.patch.object(costs.CostHandler, 'get_all_classes')
    def test_get_cost_classes_normal(self, getcls):
        self.flags(scheduler_solver_costs=['FakeCost1'],
                    group='solver_scheduler')
        getcls.return_value = [FakeCost1, FakeCost2]
        cost_classes = self.solver._get_cost_classes()
        self.assertIn(FakeCost1, cost_classes)
        self.assertNotIn(FakeCost2, cost_classes)

    @mock.patch.object(costs.CostHandler, 'get_all_classes')
    def test_get_cost_classes_not_found(self, getcls):
        self.flags(scheduler_solver_costs=['FakeUnknownCost'],
                    group='solver_scheduler')
        getcls.return_value = [FakeCost1, FakeCost2]
        self.assertRaises(exception.SchedulerSolverCostNotFound,
                self.solver._get_cost_classes)

    @mock.patch.object(constraints.ConstraintHandler, 'get_all_classes')
    def test_get_constraint_classes_normal(self, getcls):
        self.flags(scheduler_solver_constraints=['FakeConstraint1'],
                    group='solver_scheduler')
        getcls.return_value = [FakeConstraint1, FakeConstraint2]
        constraint_classes = self.solver._get_constraint_classes()
        self.assertIn(FakeConstraint1, constraint_classes)
        self.assertNotIn(FakeConstraint2, constraint_classes)

    @mock.patch.object(constraints.ConstraintHandler, 'get_all_classes')
    def test_get_constraint_classes_not_found(self, getcls):
        self.flags(scheduler_solver_constraints=['FakeUnknownConstraint'],
                    group='solver_scheduler')
        getcls.return_value = [FakeConstraint1, FakeConstraint2]
        self.assertRaises(exception.SchedulerSolverConstraintNotFound,
                self.solver._get_constraint_classes)

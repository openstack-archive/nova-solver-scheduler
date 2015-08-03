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

"""Test case for solver scheduler vCPU cost."""

from nova import context
from nova import test
from nova_solverscheduler.scheduler.solvers import costs
from nova_solverscheduler.scheduler.solvers.costs import vcpu_cost
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes


class TestVcpuCost(test.NoDBTestCase):
    def setUp(self):
        super(TestVcpuCost, self).setUp()
        self.context = context.RequestContext('fake_usr', 'fake_proj')
        self.cost_handler = costs.CostHandler()
        self.cost_classes = self.cost_handler.get_matching_classes(
            ['nova_solverscheduler.scheduler.solvers.costs.vcpu_cost.VcpuCost']
        )

    def _get_all_hosts(self):
        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1',
                {'vcpus_total': 32, 'vcpus_used': 12})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node2',
                {'vcpus_total': 16, 'vcpus_used': 6})
        host3 = fakes.FakeSolverSchedulerHostState('host3', 'node3',
                {'vcpus_total': 8, 'vcpus_used': 3})
        host4 = fakes.FakeSolverSchedulerHostState('host4', 'node4',
                {'vcpus_total': 0, 'vcpus_used': 0})
        return [host1, host2, host3, host4]

    def test_vcpu_cost_multiplier_1(self):
        self.flags(vcpu_cost_multiplier=0.5, group='solver_scheduler')
        self.assertEqual(0.5, vcpu_cost.VcpuCost().cost_multiplier())

    def test_vcpu_cost_multiplier_2(self):
        self.flags(vcpu_cost_multiplier=(-2), group='solver_scheduler')
        self.assertEqual((-2), vcpu_cost.VcpuCost().cost_multiplier())

    def test_get_extended_cost_matrix(self):
        fake_hosts = self._get_all_hosts()
        fake_filter_properties = {
                'context': self.context,
                'num_instances': 3,
                'instance_type': {'vcpus': 5},
                'instance_uuids': ['fake_uuid_%s' % x for x in range(3)]}

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [-1.0, -0.75, -0.5, -0.25],
                [-0.5, -0.25, 0.0, 0.25],
                [-0.25, 0.0, 0.25, 0.5],
                [0.0, 0.25, 0.5, 0.75]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        expected_x_cost_mat = [[round(val, 4) for val in row]
                                for row in expected_x_cost_mat]
        x_cost_mat = [[round(val, 4) for val in row] for row in x_cost_mat]
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_bad_vcpu_req(self):
        fake_hosts = self._get_all_hosts()
        fake_filter_properties = {
                'context': self.context,
                'num_instances': 3,
                'instance_type': {'vcpus': 0},
                'instance_uuids': ['fake_uuid_%s' % x for x in range(3)]}

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [-1.0, -1.0, -1.0, -1.0],
                [-0.5, -0.5, -0.5, -0.5],
                [-0.25, -0.25, -0.25, -0.25],
                [0.0, 0.0, 0.0, 0.0]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        expected_x_cost_mat = [[round(val, 4) for val in row]
                                for row in expected_x_cost_mat]
        x_cost_mat = [[round(val, 4) for val in row] for row in x_cost_mat]
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

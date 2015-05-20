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

"""Test case for solver scheduler RAM cost."""

from nova import context
from nova import test
from nova_solverscheduler.scheduler.solvers import costs
from nova_solverscheduler.scheduler.solvers.costs import ram_cost
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes


class TestRamCost(test.NoDBTestCase):
    def setUp(self):
        super(TestRamCost, self).setUp()
        self.context = context.RequestContext('fake_usr', 'fake_proj')
        self.cost_handler = costs.CostHandler()
        self.cost_classes = self.cost_handler.get_matching_classes(
            ['nova_solverscheduler.scheduler.solvers.costs.ram_cost.RamCost'])

    def _get_all_hosts(self):
        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1',
                {'free_ram_mb': 512})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node2',
                {'free_ram_mb': 1024})
        host3 = fakes.FakeSolverSchedulerHostState('host3', 'node3',
                {'free_ram_mb': 3072})
        host4 = fakes.FakeSolverSchedulerHostState('host4', 'node4',
                {'free_ram_mb': 8192})
        return [host1, host2, host3, host4]

    def test_ram_cost_multiplier_1(self):
        self.flags(ram_cost_multiplier=0.5, group='solver_scheduler')
        self.assertEqual(0.5, ram_cost.RamCost().cost_multiplier())

    def test_ram_cost_multiplier_2(self):
        self.flags(ram_cost_multiplier=(-2), group='solver_scheduler')
        self.assertEqual((-2), ram_cost.RamCost().cost_multiplier())

    def test_get_extended_cost_matrix(self):
        # the host.free_ram_mb values of these fake hosts are supposed to be:
        # 512, 1024, 3072, 8192
        fake_hosts = self._get_all_hosts()
        # FIXME: ideally should mock get_hosts_stripping_forced_and_ignored()
        fake_hosts = list(fake_hosts)
        # the hosts order may be arbitrary, here we manually order them
        # which is for convenience of testings
        tmp = []
        for i in range(len(fake_hosts)):
            for fh in fake_hosts:
                if fh.host == 'host%s' % (i + 1):
                    tmp.append(fh)
        fake_hosts = tmp
        fake_filter_properties = {
                'context': self.context.elevated(),
                'num_instances': 3,
                'instance_type': {'memory_mb': 1024},
                'instance_uuids': ['fake_uuid_%s' % x for x in range(3)]}

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [0.0, 0.125, 0.25, 0.375],
                [-0.125, 0.0, 0.125, 0.25],
                [-0.375, -0.25, -0.125, -0.0],
                [-1.0, -0.875, -0.75, -0.625]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        expected_x_cost_mat = [[round(val, 4) for val in row]
                                for row in expected_x_cost_mat]
        x_cost_mat = [[round(val, 4) for val in row] for row in x_cost_mat]
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

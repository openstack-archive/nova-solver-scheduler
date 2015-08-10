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

from nova import test
from nova_solverscheduler.scheduler.solvers.constraints \
        import exact_ram_constraint
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes


class TestExactRamConstraint(test.NoDBTestCase):

    def setUp(self):
        super(TestExactRamConstraint, self).setUp()
        self.constraint_cls = exact_ram_constraint.ExactRamConstraint

    def _gen_fake_hosts(self):
        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1',
                {'free_ram_mb': 512, 'total_usable_ram_mb': 1024})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node1',
                {'free_ram_mb': 1024, 'total_usable_ram_mb': 2048})
        host3 = fakes.FakeSolverSchedulerHostState('host3', 'node1',
                {'free_ram_mb': -256, 'total_usable_ram_mb': 512})
        hosts = [host1, host2, host3]
        return hosts

    def test_get_constraint_matrix(self):
        fake_hosts = self._gen_fake_hosts()
        fake_filter_properties = {
            'instance_type': {'memory_mb': 1024},
            'num_instances': 2}
        expected_cons_mat = [
            [False, False],
            [True, False],
            [False, False]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

    def test_get_constraint_matrix_bad_request_info(self):
        fake_hosts = self._gen_fake_hosts()
        expected_cons_mat = [
            [True, True],
            [True, True],
            [True, True]]

        fake_filter_properties = {
            'instance_type': {'memory_mb': 0},
            'num_instances': 2}
        cons_mat = self.constraint_cls().get_constraint_matrix(
                fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

        fake_filter_properties = {
            'instance_type': None,
            'num_instances': 2}
        cons_mat = self.constraint_cls().get_constraint_matrix(
                fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

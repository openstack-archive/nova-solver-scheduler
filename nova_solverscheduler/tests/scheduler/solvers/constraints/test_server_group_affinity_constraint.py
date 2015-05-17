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

from nova import test
from nova_solverscheduler.scheduler.solvers.constraints \
        import server_group_affinity_constraint
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes


class TestServerGroupAffinityConstraint(test.NoDBTestCase):

    def setUp(self):
        super(TestServerGroupAffinityConstraint, self).setUp()
        self.constraint_cls = \
                server_group_affinity_constraint.ServerGroupAffinityConstraint
        self._generate_fake_constraint_input()

    def _generate_fake_constraint_input(self):
        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1', {})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node1', {})
        host3 = fakes.FakeSolverSchedulerHostState('host3', 'node1', {})
        self.fake_hosts = [host1, host2, host3]

    def test_get_constraint_matrix(self):
        fake_filter_properties = {
                'group_policies': ['affinity'],
                'group_hosts': ['host2'],
                'instance_uuids': ['fake_uuid_%s' % x for x in range(2)],
                'num_instances': 2}
        expected_cons_mat = [
            [False, False],
            [True, True],
            [False, False]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

    def test_get_constraint_matrix_empty_group_hosts_list(self):
        fake_filter_properties = {
                'group_policies': ['affinity'],
                'group_hosts': [],
                'instance_uuids': ['fake_uuid_%s' % x for x in range(2)],
                'num_instances': 2}
        expected_cons_mat = [
            [False, True],
            [False, True],
            [False, True]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

    def test_get_constraint_matrix_wrong_policy(self):
        fake_filter_properties = {
                'group_policies': ['other'],
                'instance_uuids': ['fake_uuid_%s' % x for x in range(2)],
                'num_instances': 2}
        expected_cons_mat = [
            [True, True],
            [True, True],
            [True, True]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)


class TestServerGroupAntiAffinityConstraint(test.NoDBTestCase):

    def setUp(self):
        super(TestServerGroupAntiAffinityConstraint, self).setUp()
        self.constraint_cls = server_group_affinity_constraint.\
                                            ServerGroupAntiAffinityConstraint
        self._generate_fake_constraint_input()

    def _generate_fake_constraint_input(self):
        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1', {})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node1', {})
        host3 = fakes.FakeSolverSchedulerHostState('host3', 'node1', {})
        self.fake_hosts = [host1, host2, host3]

    def test_get_constraint_matrix(self):
        fake_filter_properties = {
                'group_policies': ['anti-affinity'],
                'group_hosts': ['host1', 'host3'],
                'instance_uuids': ['fake_uuid_%s' % x for x in range(2)],
                'num_instances': 2}
        expected_cons_mat = [
            [False, False],
            [True, False],
            [False, False]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

    def test_get_constraint_matrix_empty_group_hosts_list(self):
        fake_filter_properties = {
                'group_policies': ['anti-affinity'],
                'group_hosts': [],
                'instance_uuids': ['fake_uuid_%s' % x for x in range(2)],
                'num_instances': 2}
        expected_cons_mat = [
            [True, False],
            [True, False],
            [True, False]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

    def test_get_constraint_matrix_wrong_policy(self):
        fake_filter_properties = {
                'group_policies': ['other'],
                'instance_uuids': ['fake_uuid_%s' % x for x in range(2)],
                'num_instances': 2}
        expected_cons_mat = [
            [True, True],
            [True, True],
            [True, True]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

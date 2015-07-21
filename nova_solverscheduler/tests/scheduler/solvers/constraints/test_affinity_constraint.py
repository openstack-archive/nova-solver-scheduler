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

from nova import context
from nova import test
from nova_solverscheduler.scheduler.solvers.constraints \
        import affinity_constraint
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes


class TestSameHostConstraint(test.NoDBTestCase):
    USES_DB = True

    def setUp(self):
        super(TestSameHostConstraint, self).setUp()
        self.constraint_cls = affinity_constraint.SameHostConstraint

        self.context = context.RequestContext('fake_usr', 'fake_proj')

        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1', {})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node1', {})
        self.fake_hosts = [host1, host2]

        instance1 = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host1'})
        instance2 = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host2'})
        instance3 = fakes.FakeInstance(context=self.context,
                                        params={})
        uuid_1 = instance1.uuid
        uuid_2 = instance2.uuid
        uuid_3 = instance3.uuid
        self.fake_instances = [instance1, instance2, instance3]
        self.fake_instance_uuids = [uuid_1, uuid_2, uuid_3]

    def test_get_constraint_matrix_normal(self):
        fake_filter_properties = {
                'context': self.context,
                'scheduler_hints': {'same_host': self.fake_instance_uuids[0]},
                'num_instances': 3}
        expected_cons_mat = [
            [True, True, True],
            [False, False, False]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

        fake_filter_properties = {
                'context': self.context,
                'scheduler_hints': {'same_host':
                                    self.fake_instance_uuids[0:2]},
                'num_instances': 3}
        expected_cons_mat = [
            [True, True, True],
            [True, True, True]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

    def test_get_constraint_matrix_reject(self):
        fake_filter_properties = {
                'context': self.context,
                'scheduler_hints': {'same_host':
                                    ['unknown_uuid_1', 'unknown_uuid_2']},
                'num_instances': 3}
        expected_cons_mat = [
            [False, False, False],
            [False, False, False]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

        fake_filter_properties = {
                'context': self.context,
                'scheduler_hints': {'same_host': self.fake_instance_uuids},
                'num_instances': 3}
        expected_cons_mat = [
            [False, False, False],
            [False, False, False]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

    def test_get_constraint_matrix_nohint(self):
        fake_filter_properties = {
                'context': self.context,
                'num_instances': 3}
        expected_cons_mat = [
            [True, True, True],
            [True, True, True]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)


class TestDifferentHostConstraint(test.NoDBTestCase):
    USES_DB = True

    def setUp(self):
        super(TestDifferentHostConstraint, self).setUp()
        self.constraint_cls = affinity_constraint.DifferentHostConstraint

        self.context = context.RequestContext('fake_usr', 'fake_proj')

        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1', {})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node1', {})
        self.fake_hosts = [host1, host2]

        instance1 = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host1'})
        instance2 = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host2'})
        instance3 = fakes.FakeInstance(context=self.context,
                                        params={})
        uuid_1 = instance1.uuid
        uuid_2 = instance2.uuid
        uuid_3 = instance3.uuid
        self.fake_instances = [instance1, instance2, instance3]
        self.fake_instance_uuids = [uuid_1, uuid_2, uuid_3]

    def test_get_constraint_matrix_normal(self):
        fake_filter_properties = {
                'context': self.context,
                'scheduler_hints': {'different_host':
                                    self.fake_instance_uuids[0]},
                'num_instances': 3}
        expected_cons_mat = [
            [False, False, False],
            [True, True, True]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

        fake_filter_properties = {
                'context': self.context,
                'scheduler_hints': {'different_host':
                                    self.fake_instance_uuids[0:2]},
                'num_instances': 3}
        expected_cons_mat = [
            [False, False, False],
            [False, False, False]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

    def test_get_constraint_matrix_reject(self):
        fake_filter_properties = {
                'context': self.context,
                'scheduler_hints': {'different_host':
                                    ['unknown_uuid_1', 'unknown_uuid_2']},
                'num_instances': 3}
        expected_cons_mat = [
            [False, False, False],
            [False, False, False]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

        fake_filter_properties = {
                'context': self.context,
                'scheduler_hints': {'different_host':
                                    self.fake_instance_uuids},
                'num_instances': 3}
        expected_cons_mat = [
            [False, False, False],
            [False, False, False]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

    def test_get_constraint_matrix_nohint(self):
        fake_filter_properties = {
                'context': self.context,
                'num_instances': 3}
        expected_cons_mat = [
            [True, True, True],
            [True, True, True]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)


class TestSimpleCidrAffinityConstraint(test.NoDBTestCase):

    def setUp(self):
        super(TestSimpleCidrAffinityConstraint, self).setUp()
        self.constraint_cls = affinity_constraint.SimpleCidrAffinityConstraint
        self._generate_fake_constraint_input()

    def _generate_fake_constraint_input(self):
        self.fake_filter_properties = {
                'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
                'num_instances': 3}
        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1', {})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node1', {})
        self.fake_hosts = [host1, host2]

    @mock.patch('nova_solverscheduler.scheduler.solvers.constraints.'
                'affinity_constraint.SimpleCidrAffinityConstraint.'
                'host_filter_cls')
    def test_get_constraint_matrix(self, mock_filter_cls):
        expected_cons_mat = [
            [True, True, True],
            [False, False, False]]
        mock_filter = mock_filter_cls.return_value
        mock_filter.host_passes.side_effect = [True, False]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, self.fake_filter_properties)
        self.assertEqual(expected_cons_mat, cons_mat)

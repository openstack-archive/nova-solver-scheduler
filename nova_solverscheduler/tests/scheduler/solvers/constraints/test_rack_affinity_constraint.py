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

from nova import context
from nova import test
from nova_solverscheduler.scheduler.solvers.constraints \
        import rack_affinity_constraint
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes


class TestRackSorting(test.NoDBTestCase):

    def setUp(self):
        super(TestRackSorting, self).setUp()
        self.fake_hosts = [fakes.FakeSolverSchedulerHostState(
                        'host%s' % i, 'node1', {}) for i in xrange(1, 7)]

    def test_get_sorted_racks_normal(self):
        """Let number of available instances: rack1 = rack3 < rack2, and
        present host costs: rack3 < rack2 < rack1. The sorted racks should
        be: rack2, rack3, rack1.
        """
        fake_racks_list = ['rack1', 'rack2', 'rack3']

        fake_cost_matrix = [
            [5, 5, 5],
            [4, 4, 4],
            [3, 3, 3],
            [2, 2, 2],
            [1, 1, 1],
            [0, 0, 0]
        ]
        fake_constraint_matrix = [
            [True, True, False],
            [True, False, False],
            [True, True, True],
            [True, True, True],
            [False, False, False],
            [True, True, True]
        ]

        fake_filter_properties = {
            'num_instances': 3,
            'solver_cache': {'cost_matrix': fake_cost_matrix,
                            'constraint_matrix': fake_constraint_matrix}
        }

        fake_host_racks_map = {
            'host1': set(['rack1']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_result = ['rack2', 'rack3', 'rack1']
        result = rack_affinity_constraint._get_sorted_racks(fake_racks_list,
                self.fake_hosts, fake_host_racks_map, fake_filter_properties)
        self.assertEqual(expected_result, result)

    def test_get_sorted_racks_normal_shorter_input_racks_list(self):
        fake_racks_list = ['rack1', 'rack2']

        fake_cost_matrix = [
            [5, 5, 5],
            [4, 4, 4],
            [3, 3, 3],
            [2, 2, 2],
            [1, 1, 1],
            [0, 0, 0]
        ]
        fake_constraint_matrix = [
            [True, True, False],
            [True, False, False],
            [True, True, True],
            [True, True, True],
            [False, False, False],
            [True, True, True]
        ]

        fake_filter_properties = {
            'num_instances': 3,
            'solver_cache': {'cost_matrix': fake_cost_matrix,
                            'constraint_matrix': fake_constraint_matrix}
        }

        fake_host_racks_map = {
            'host1': set(['rack1']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_result = ['rack2', 'rack1']
        result = rack_affinity_constraint._get_sorted_racks(fake_racks_list,
                self.fake_hosts, fake_host_racks_map, fake_filter_properties)
        self.assertEqual(expected_result, result)

    def test_get_sorted_racks_no_cost_matrix(self):
        fake_racks_list = ['rack1', 'rack2', 'rack3']

        fake_cost_matrix = []
        fake_constraint_matrix = [
            [True, True, False],
            [True, False, False],
            [True, True, True],
            [True, True, True],
            [False, False, False],
            [True, True, True]
        ]

        fake_filter_properties = {
            'num_instances': 3,
            'solver_cache': {'cost_matrix': fake_cost_matrix,
                            'constraint_matrix': fake_constraint_matrix}
        }

        fake_host_racks_map = {
            'host1': set(['rack1']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_result_idx0 = 'rack2'
        result = rack_affinity_constraint._get_sorted_racks(fake_racks_list,
                self.fake_hosts, fake_host_racks_map, fake_filter_properties)
        self.assertEqual(expected_result_idx0, result[0])

    def test_get_sorted_racks_no_constraint_matrix(self):
        fake_racks_list = ['rack1', 'rack2', 'rack3']

        fake_cost_matrix = [
            [5, 5, 5],
            [4, 4, 4],
            [3, 3, 3],
            [2, 2, 2],
            [1, 1, 1],
            [0, 0, 0]
        ]
        fake_constraint_matrix = []

        fake_filter_properties = {
            'num_instances': 3,
            'solver_cache': {'cost_matrix': fake_cost_matrix,
                            'constraint_matrix': fake_constraint_matrix}
        }

        fake_host_racks_map = {
            'host1': set(['rack1']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_result = ['rack1', 'rack2', 'rack3']
        result = rack_affinity_constraint._get_sorted_racks(fake_racks_list,
                self.fake_hosts, fake_host_racks_map, fake_filter_properties)
        self.assertEqual(expected_result, result)

    def test_get_sorted_racks_no_host_racks_map(self):
        fake_racks_list = ['rack1', 'rack2', 'rack3']

        fake_cost_matrix = [
            [5, 5, 5],
            [4, 4, 4],
            [3, 3, 3],
            [2, 2, 2],
            [1, 1, 1],
            [0, 0, 0]
        ]
        fake_constraint_matrix = [
            [True, True, False],
            [True, False, False],
            [True, True, True],
            [True, True, True],
            [False, False, False],
            [True, True, True]
        ]

        fake_filter_properties = {
            'num_instances': 3,
            'solver_cache': {'cost_matrix': fake_cost_matrix,
                            'constraint_matrix': fake_constraint_matrix}
        }

        fake_host_racks_map = {}

        expected_result = []
        result = rack_affinity_constraint._get_sorted_racks(fake_racks_list,
                self.fake_hosts, fake_host_racks_map, fake_filter_properties)
        self.assertEqual(expected_result, result)


@mock.patch('nova.db.aggregate_host_get_by_metadata_key')
class TestSameRackConstraint(test.NoDBTestCase):
    USES_DB = True

    def setUp(self):
        super(TestSameRackConstraint, self).setUp()
        self.constraint_cls = rack_affinity_constraint.SameRackConstraint
        self.context = context.RequestContext('fake', 'fake')
        self.fake_hosts = [fakes.FakeSolverSchedulerHostState(
                        'host%s' % i, 'node1', {}) for i in xrange(1, 7)]

    def test_same_rack_one_inst(self, agg_mock):
        instance = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host2'})
        instance_uuid = instance.uuid

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'same_rack': instance_uuid}
        }

        agg_mock.return_value = {
            'host1': set(['rack1']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [True, True],
            [True, True],
            [False, False],
            [False, False],
            [False, False],
            [False, False]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_same_rack_multi_inst(self, agg_mock):
        instance1 = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host1'})
        instance2 = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host3'})
        instance1_uuid = instance1.uuid
        instance2_uuid = instance2.uuid

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'same_rack': [instance1_uuid, instance2_uuid]}
        }

        agg_mock.return_value = {
            'host1': set(['rack1']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [True, True],
            [True, True],
            [True, True],
            [True, True],
            [False, False],
            [False, False]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_same_rack_with_cross_rack_host(self, agg_mock):
        instance = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host1'})
        instance_uuid = instance.uuid

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'same_rack': instance_uuid}
        }

        agg_mock.return_value = {
            'host1': set(['rack1', 'rack2']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [True, True],
            [True, True],
            [True, True],
            [True, True],
            [False, False],
            [False, False]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_same_rack_incomplete_rack_config(self, agg_mock):
        instance = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host2'})
        instance_uuid = instance.uuid

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'same_rack': instance_uuid}
        }

        agg_mock.return_value = {
            'host1': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [False, False],
            [True, True],
            [False, False],
            [False, False],
            [False, False],
            [False, False]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_same_rack_incomplete_rack_config2(self, agg_mock):
        instance = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host3'})
        instance_uuid = instance.uuid

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'same_rack': instance_uuid}
        }

        agg_mock.return_value = {
            'host1': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [False, False],
            [False, False],
            [True, True],
            [True, True],
            [False, False],
            [False, False]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_same_rack_no_rack_config(self, agg_mock):
        instance = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host2'})
        instance_uuid = instance.uuid

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'same_rack': instance_uuid}
        }

        agg_mock.return_value = {}

        expected_cons_mat = [
            [False, False],
            [True, True],
            [False, False],
            [False, False],
            [False, False],
            [False, False]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)


@mock.patch('nova.db.aggregate_host_get_by_metadata_key')
class TestDifferentRackConstraint(test.NoDBTestCase):
    USES_DB = True

    def setUp(self):
        super(TestDifferentRackConstraint, self).setUp()
        self.constraint_cls = rack_affinity_constraint.DifferentRackConstraint
        self.context = context.RequestContext('fake', 'fake')
        self.fake_hosts = [fakes.FakeSolverSchedulerHostState(
                        'host%s' % i, 'node1', {}) for i in xrange(1, 7)]

    def test_different_rack_one_inst(self, agg_mock):
        instance = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host2'})
        instance_uuid = instance.uuid

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'different_rack': instance_uuid}
        }

        agg_mock.return_value = {
            'host1': set(['rack1']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [False, False],
            [False, False],
            [True, True],
            [True, True],
            [True, True],
            [True, True]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_different_rack_multi_inst(self, agg_mock):
        instance1 = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host1'})
        instance2 = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host3'})
        instance1_uuid = instance1.uuid
        instance2_uuid = instance2.uuid

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'different_rack':
                                [instance1_uuid, instance2_uuid]}
        }

        agg_mock.return_value = {
            'host1': set(['rack1']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [False, False],
            [False, False],
            [False, False],
            [False, False],
            [True, True],
            [True, True]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_different_rack_with_cross_rack_host(self, agg_mock):
        instance = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host1'})
        instance_uuid = instance.uuid

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'different_rack': instance_uuid}
        }

        agg_mock.return_value = {
            'host1': set(['rack1', 'rack2']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [False, False],
            [False, False],
            [False, False],
            [False, False],
            [True, True],
            [True, True]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_different_rack_incomplete_rack_config(self, agg_mock):
        instance = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host2'})
        instance_uuid = instance.uuid

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'different_rack': instance_uuid}
        }

        agg_mock.return_value = {
            'host1': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [True, True],
            [False, False],
            [True, True],
            [True, True],
            [True, True],
            [True, True]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_different_rack_incomplete_rack_config2(self, agg_mock):
        instance = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host3'})
        instance_uuid = instance.uuid

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'different_rack': instance_uuid}
        }

        agg_mock.return_value = {
            'host1': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [True, True],
            [True, True],
            [False, False],
            [False, False],
            [True, True],
            [True, True]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_different_rack_no_rack_config(self, agg_mock):
        instance = fakes.FakeInstance(context=self.context,
                                        params={'host': 'host2'})
        instance_uuid = instance.uuid

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'different_rack': instance_uuid}
        }

        agg_mock.return_value = {}

        expected_cons_mat = [
            [True, True],
            [False, False],
            [True, True],
            [True, True],
            [True, True],
            [True, True]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)


@mock.patch('nova.db.aggregate_host_get_by_metadata_key')
class TestTenantRackConstraint(test.NoDBTestCase):

    def setUp(self):
        super(TestTenantRackConstraint, self).setUp()
        self.constraint_cls = rack_affinity_constraint.\
                                                TenantRackConstraint
        self.context = context.RequestContext('fake', 'fake')
        self.fake_hosts = [fakes.FakeSolverSchedulerHostState(
                        'host%s' % i, 'node1', {'projects': []})
                        for i in xrange(1, 7)]

    def test_tenant_rack_max_racks_reached(self, agg_mock):
        self.flags(max_racks_per_tenant=2)

        # let the tenant vm's be in host1, host3
        self.fake_hosts[0].projects = ['fake']
        self.fake_hosts[2].projects = ['fake']

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2
        }

        agg_mock.return_value = {
            'host1': set(['rack1']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [True, True],
            [True, True],
            [True, True],
            [True, True],
            [False, False],
            [False, False]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_tenant_rack_choose_additional_racks1(self, agg_mock):
        """sort additional racks by available instances number"""
        self.flags(max_racks_per_tenant=2)

        # let the tenant vm's be in host1
        self.fake_hosts[0].projects = ['fake']

        fake_cost_matrix = [
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 4],
            [4, 5],
            [5, 6]
        ]
        fake_constraint_matrix = [
            [True, True],
            [True, True],
            [True, False],
            [False, False],
            [True, True],
            [False, False]
        ]

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'solver_cache': {'cost_matrix': fake_cost_matrix,
                            'constraint_matrix': fake_constraint_matrix}
        }

        agg_mock.return_value = {
            'host1': set(['rack1']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [True, True],
            [True, True],
            [False, False],
            [False, False],
            [True, True],
            [True, True]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_tenant_rack_choose_additional_racks2(self, agg_mock):
        """sort additional racks by costs when available num_hosts are same."""
        self.flags(max_racks_per_tenant=2)

        # let the tenant vm's be in host1
        self.fake_hosts[0].projects = ['fake']

        fake_cost_matrix = [
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 4],
            [4, 5],
            [5, 6]
        ]
        fake_constraint_matrix = [
            [True, True],
            [True, True],
            [True, True],
            [False, False],
            [True, True],
            [False, False]
        ]

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'solver_cache': {'cost_matrix': fake_cost_matrix,
                            'constraint_matrix': fake_constraint_matrix}
        }

        agg_mock.return_value = {
            'host1': set(['rack1']),
            'host2': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host5': set(['rack3']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [True, True],
            [True, True],
            [True, True],
            [True, True],
            [False, False],
            [False, False]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_tenant_rack_incomplete_rack_config(self, agg_mock):
        self.flags(max_racks_per_tenant=1)

        # let the tenant vm's be in host2, host3
        self.fake_hosts[1].projects = ['fake']
        self.fake_hosts[2].projects = ['fake']

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2
        }

        agg_mock.return_value = {
            'host1': set(['rack1']),
            'host3': set(['rack2']),
            'host4': set(['rack2']),
            'host6': set(['rack3'])
        }

        expected_cons_mat = [
            [False, False],
            [True, True],
            [True, True],
            [True, True],
            [True, True],
            [False, False]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

    def test_tenant_rack_no_rack_config(self, agg_mock):
        self.flags(max_racks_per_tenant=1)

        # let the tenant vm's be in host2, host3
        self.fake_hosts[1].projects = ['fake']
        self.fake_hosts[2].projects = ['fake']

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2
        }

        agg_mock.return_value = {}

        expected_cons_mat = [
            [True, True],
            [True, True],
            [True, True],
            [True, True],
            [True, True],
            [True, True]
        ]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                                    self.fake_hosts, fake_filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

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
from nova import objects
from nova import test
from nova_solverscheduler.scheduler.solvers.constraints \
        import rack_affinity_constraint
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes


@mock.patch('nova_solverscheduler.scheduler.solvers.utils.get_host_racks_map')
class TestSameRackConstraint(test.NoDBTestCase):

    def setUp(self):
        super(TestSameRackConstraint, self).setUp()
        self.constraint_cls = rack_affinity_constraint.SameRackConstraint
        self.context = context.RequestContext('fake', 'fake')
        self.fake_hosts = [fakes.FakeSolverSchedulerHostState(
                        'host%s' % i, 'node1', {}) for i in xrange(1, 7)]

    def test_same_rack_one_inst(self, racks_mock):
        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host2
        self.fake_hosts[1].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'same_rack': instance_uuid}
        }

        racks_mock.return_value = {
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

    def test_same_rack_multi_inst(self, racks_mock):
        instance1 = objects.Instance(uuid='inst1')
        instance2 = objects.Instance(uuid='inst2')
        instance1_uuid = instance1.uuid
        instance2_uuid = instance2.uuid
        # let these instances be in host1 and host3
        self.fake_hosts[0].instances = {instance1_uuid: instance1}
        self.fake_hosts[2].instances = {instance2_uuid: instance2}

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'same_rack': [instance1_uuid, instance2_uuid]}
        }

        racks_mock.return_value = {
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

    def test_same_rack_with_cross_rack_host(self, racks_mock):
        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host1
        self.fake_hosts[0].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'same_rack': instance_uuid}
        }

        racks_mock.return_value = {
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

    def test_same_rack_incomplete_rack_config(self, racks_mock):
        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host2
        self.fake_hosts[1].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'same_rack': instance_uuid}
        }

        racks_mock.return_value = {
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

    def test_same_rack_incomplete_rack_config2(self, racks_mock):
        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host3
        self.fake_hosts[2].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'same_rack': instance_uuid}
        }

        racks_mock.return_value = {
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

    def test_same_rack_no_rack_config(self, racks_mock):
        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host2
        self.fake_hosts[1].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'same_rack': instance_uuid}
        }

        racks_mock.return_value = {}

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


@mock.patch('nova_solverscheduler.scheduler.solvers.utils.get_host_racks_map')
class TestDifferentRackConstraint(test.NoDBTestCase):

    def setUp(self):
        super(TestDifferentRackConstraint, self).setUp()
        self.constraint_cls = rack_affinity_constraint.DifferentRackConstraint
        self.context = context.RequestContext('fake', 'fake')
        self.fake_hosts = [fakes.FakeSolverSchedulerHostState(
                        'host%s' % i, 'node1', {}) for i in xrange(1, 7)]

    def test_different_rack_one_inst(self, racks_mock):
        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host2
        self.fake_hosts[1].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'different_rack': instance_uuid}
        }

        racks_mock.return_value = {
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

    def test_different_rack_multi_inst(self, racks_mock):
        instance1 = objects.Instance(uuid='inst1')
        instance2 = objects.Instance(uuid='inst2')
        instance1_uuid = instance1.uuid
        instance2_uuid = instance2.uuid
        # let these instances be in host1 and host3
        self.fake_hosts[0].instances = {instance1_uuid: instance1}
        self.fake_hosts[2].instances = {instance2_uuid: instance2}

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'different_rack':
                                [instance1_uuid, instance2_uuid]}
        }

        racks_mock.return_value = {
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

    def test_different_rack_with_cross_rack_host(self, racks_mock):
        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host1
        self.fake_hosts[0].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'different_rack': instance_uuid}
        }

        racks_mock.return_value = {
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

    def test_different_rack_incomplete_rack_config(self, racks_mock):
        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host2
        self.fake_hosts[1].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'different_rack': instance_uuid}
        }

        racks_mock.return_value = {
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

    def test_different_rack_incomplete_rack_config2(self, racks_mock):
        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host3
        self.fake_hosts[2].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'different_rack': instance_uuid}
        }

        racks_mock.return_value = {
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

    def test_different_rack_no_rack_config(self, racks_mock):
        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host2
        self.fake_hosts[1].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context,
            'project_id': 'fake',
            'num_instances': 2,
            'scheduler_hints': {'different_rack': instance_uuid}
        }

        racks_mock.return_value = {}

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

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

"""Test case for solver scheduler affinity-cost."""

from nova import context
from nova import objects
from nova import test
from nova_solverscheduler.scheduler.solvers import costs
from nova_solverscheduler.scheduler.solvers.costs import affinity_cost
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes


class TestAffinityCost(test.NoDBTestCase):
    USES_DB = True

    def setUp(self):
        super(TestAffinityCost, self).setUp()
        self.context = context.RequestContext('fake_usr', 'fake_proj')
        self.cost_handler = costs.CostHandler()
        self.cost_classes = self.cost_handler.get_matching_classes(
                ['nova_solverscheduler.scheduler.solvers.costs.'
                'affinity_cost.AffinityCost'])

    def _get_fake_hosts(self):
        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1', {})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node2', {})
        host3 = fakes.FakeSolverSchedulerHostState('host3', 'node3', {})
        host4 = fakes.FakeSolverSchedulerHostState('host4', 'node4', {})
        return [host1, host2, host3, host4]

    def test_affinity_cost_multiplier(self):
        self.flags(affinity_cost_multiplier=0.5, group='solver_scheduler')
        self.assertEqual(0.5, affinity_cost.AffinityCost().cost_multiplier())

    def test_get_extended_cost_matrix_one_inst(self):
        fake_hosts = self._get_fake_hosts()

        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host2
        fake_hosts[1].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context.elevated(),
            'num_instances': 3,
            'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
            'scheduler_hints': {'soft_same_host': instance_uuid}
        }

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [1, 0, -1, -2],
                [0, -1, -2, -3],
                [1, 0, -1, -2],
                [1, 0, -1, -2]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_multi_inst(self):
        fake_hosts = self._get_fake_hosts()

        instance1 = objects.Instance(uuid='inst1')
        instance2 = objects.Instance(uuid='inst2')
        instance1_uuid = instance1.uuid
        instance2_uuid = instance2.uuid
        # let these instances be in host1 and host3
        fake_hosts[0].instances = {instance1_uuid: instance1}
        fake_hosts[2].instances = {instance2_uuid: instance2}

        fake_filter_properties = {
            'context': self.context.elevated(),
            'num_instances': 3,
            'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
            'scheduler_hints': {'soft_same_host':
                                [instance1_uuid, instance2_uuid]}
        }

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [0, -1, -2, -3],
                [1, 0, -1, -2],
                [0, -1, -2, -3],
                [1, 0, -1, -2]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_change_multiplier(self):
        self.flags(affinity_cost_multiplier=0.5, group='solver_scheduler')

        fake_hosts = self._get_fake_hosts()

        instance1 = objects.Instance(uuid='inst1')
        instance2 = objects.Instance(uuid='inst2')
        instance1_uuid = instance1.uuid
        instance2_uuid = instance2.uuid
        # let these instances be in host1 and host3
        fake_hosts[0].instances = {instance1_uuid: instance1}
        fake_hosts[2].instances = {instance2_uuid: instance2}

        fake_filter_properties = {
            'context': self.context.elevated(),
            'num_instances': 3,
            'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
            'scheduler_hints': {'soft_same_host':
                                [instance1_uuid, instance2_uuid]}
        }

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [0, -2, -4, -6],
                [1, -1, -3, -5],
                [0, -2, -4, -6],
                [1, -1, -3, -5]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_zero_multiplier(self):
        self.flags(affinity_cost_multiplier=0, group='solver_scheduler')

        fake_hosts = self._get_fake_hosts()

        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host2
        fake_hosts[1].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context.elevated(),
            'num_instances': 3,
            'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
            'scheduler_hints': {'soft_same_host': instance_uuid}
        }

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_no_instance_list(self):
        fake_hosts = self._get_fake_hosts()

        fake_filter_properties = {
            'context': self.context.elevated(),
            'num_instances': 3,
            'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
            'scheduler_hints': {'soft_same_host': ''}
        }

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [-0, -1, -2, -3],
                [-0, -1, -2, -3],
                [-0, -1, -2, -3],
                [-0, -1, -2, -3]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_no_hint(self):
        fake_hosts = self._get_fake_hosts()

        fake_filter_properties = {
            'context': self.context.elevated(),
            'num_instances': 3,
            'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
            'scheduler_hints': {}
        }

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        self.assertEqual(expected_x_cost_mat, x_cost_mat)


class TestAntiAffinityCost(test.NoDBTestCase):
    USES_DB = True

    def setUp(self):
        super(TestAntiAffinityCost, self).setUp()
        self.context = context.RequestContext('fake_usr', 'fake_proj')
        self.cost_handler = costs.CostHandler()
        self.cost_classes = self.cost_handler.get_matching_classes(
            ['nova_solverscheduler.scheduler.solvers.costs.'
            'affinity_cost.AntiAffinityCost'])

    def _get_fake_hosts(self):
        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1', {})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node2', {})
        host3 = fakes.FakeSolverSchedulerHostState('host3', 'node3', {})
        host4 = fakes.FakeSolverSchedulerHostState('host4', 'node4', {})
        return [host1, host2, host3, host4]

    def test_anti_affinity_cost_multiplier(self):
        self.flags(anti_affinity_cost_multiplier=2, group='solver_scheduler')
        self.assertEqual(2,
                        affinity_cost.AntiAffinityCost().cost_multiplier())

    def test_get_extended_cost_matrix_one_inst(self):
        fake_hosts = self._get_fake_hosts()

        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host2
        fake_hosts[1].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context.elevated(),
            'num_instances': 3,
            'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
            'scheduler_hints': {'soft_different_host': instance_uuid}
        }

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [0, 1, 2, 3],
                [1, 2, 3, 4],
                [0, 1, 2, 3],
                [0, 1, 2, 3]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_multi_inst(self):
        fake_hosts = self._get_fake_hosts()

        instance1 = objects.Instance(uuid='inst1')
        instance2 = objects.Instance(uuid='inst2')
        instance1_uuid = instance1.uuid
        instance2_uuid = instance2.uuid
        # let these instances be in host1 and host3
        fake_hosts[0].instances = {instance1_uuid: instance1}
        fake_hosts[2].instances = {instance2_uuid: instance2}

        fake_filter_properties = {
            'context': self.context.elevated(),
            'num_instances': 3,
            'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
            'scheduler_hints': {'soft_different_host':
                                [instance1_uuid, instance2_uuid]}
        }

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [1, 2, 3, 4],
                [0, 1, 2, 3],
                [1, 2, 3, 4],
                [0, 1, 2, 3]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_change_multiplier(self):
        self.flags(anti_affinity_cost_multiplier=0.5,
                    group='solver_scheduler')

        fake_hosts = self._get_fake_hosts()

        instance1 = objects.Instance(uuid='inst1')
        instance2 = objects.Instance(uuid='inst2')
        instance1_uuid = instance1.uuid
        instance2_uuid = instance2.uuid
        # let these instances be in host1 and host3
        fake_hosts[0].instances = {instance1_uuid: instance1}
        fake_hosts[2].instances = {instance2_uuid: instance2}

        fake_filter_properties = {
            'context': self.context.elevated(),
            'num_instances': 3,
            'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
            'scheduler_hints': {'soft_different_host':
                                [instance1_uuid, instance2_uuid]}
        }

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [1, 3, 5, 7],
                [0, 2, 4, 6],
                [1, 3, 5, 7],
                [0, 2, 4, 6]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_zero_multiplier(self):
        self.flags(anti_affinity_cost_multiplier=0, group='solver_scheduler')

        fake_hosts = self._get_fake_hosts()

        instance = objects.Instance(uuid='inst1')
        instance_uuid = instance.uuid
        # let this instance be in host2
        fake_hosts[1].instances = {instance_uuid: instance}

        fake_filter_properties = {
            'context': self.context.elevated(),
            'num_instances': 3,
            'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
            'scheduler_hints': {'soft_different_host': instance_uuid}
        }

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_no_instance_list(self):
        fake_hosts = self._get_fake_hosts()

        fake_filter_properties = {
            'context': self.context.elevated(),
            'num_instances': 3,
            'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
            'scheduler_hints': {'soft_different_host': ''}
        }

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [0, 1, 2, 3],
                [0, 1, 2, 3],
                [0, 1, 2, 3],
                [0, 1, 2, 3]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_no_hint(self):
        fake_hosts = self._get_fake_hosts()

        fake_filter_properties = {
            'context': self.context.elevated(),
            'num_instances': 3,
            'instance_uuids': ['fake_uuid_%s' % x for x in range(3)],
            'scheduler_hints': {}
        }

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

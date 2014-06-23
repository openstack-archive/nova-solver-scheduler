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

"""
Tests for solver scheduler costs.
"""

from nova import context
from nova.scheduler.solvers import costs
from nova import test
from nova.tests.scheduler import fakes


class CostsTestBase(test.TestCase):
    """Base test case for costs."""
    def setUp(self):
        super(CostsTestBase, self).setUp()
        self.context = context.RequestContext('fake', 'fake')
        cost_handler = costs.CostHandler()
        classes = cost_handler.get_matching_classes(
                    ['nova.scheduler.solvers.costs.all_costs'])
        self.class_map = {}
        for cls in classes:
            self.class_map[cls.__name__] = cls


class AllCostsTestCase(CostsTestBase):
    """Test case for existence of all cost classes."""
    def test_all_costs(self):
        self.assertIn('RamCost', self.class_map)


class BaseCostTestCase(CostsTestBase):
    """Test case for BaseCost."""
    def test_normalize_cost_matrix_default(self):
        cost_cls = costs.BaseCost()
        cost_matrix = [[-1.0, 2.0], [3.0, 4.0]]
        output = cost_cls.normalize_cost_matrix(cost_matrix)

        ref_output = [[0.0, 0.6], [0.8, 1.0]]
        self.assertEqual(output, ref_output)

    def test_normalize_cost_matrix_custom_bounds(self):
        cost_cls = costs.BaseCost()
        cost_matrix = [[1.0, 2.0], [3.0, 4.0]]
        output = cost_cls.normalize_cost_matrix(cost_matrix, -1.0, 2.0)

        ref_output = [[-1.0, 0.0], [1.0, 2.0]]
        self.assertEqual(output, ref_output)


class RamCostTestCase(CostsTestBase):
    """Test case for RamCost."""
    def test_get_cost_matrix_single(self):
        self.flags(ram_weight_multiplier=-1.0)
        cost_cls = self.class_map['RamCost']()
        host1 = fakes.FakeHostState('host1', 'node1', {})
        hosts = [host1]
        fake_instance_uuid = 'fake-instance-id'
        instance_uuids = [fake_instance_uuid]
        request_spec = {'instance_type': 'fake_type',
                        'instance_uuids': instance_uuids}
        filter_properties = {'context': self.context.elevated()}

        cost_matrix = cost_cls.get_cost_matrix(hosts, instance_uuids,
                                            request_spec, filter_properties)
        ref_cost_matrix = [[host1.free_ram_mb * (-1.0)]]
        self.assertEqual(cost_matrix, ref_cost_matrix)

    def test_get_cost_matrix_multi(self):
        self.flags(ram_weight_multiplier=1.0)
        cost_cls = self.class_map['RamCost']()
        host1 = fakes.FakeHostState('host1', 'node1', {})
        host2 = fakes.FakeHostState('host2', 'node2', {})
        hosts = [host1, host2]
        fake_instance1_uuid = 'fake-instance1-id'
        fake_instance2_uuid = 'fake-instance2-id'
        instance_uuids = [fake_instance1_uuid, fake_instance2_uuid]
        request_spec = {'instance_type': 'fake_type',
                        'instance_uuids': instance_uuids,
                        'num_instances': 2}
        filter_properties = {'context': self.context.elevated()}

        cost_matrix = cost_cls.get_cost_matrix(hosts, instance_uuids,
                                            request_spec, filter_properties)

        ref_cost_matrix = [[host1.free_ram_mb * 1.0, host1.free_ram_mb * 1.0],
                           [host2.free_ram_mb * 1.0, host2.free_ram_mb * 1.0]]
        self.assertEqual(cost_matrix, ref_cost_matrix)

    def test_get_cost_matrix_broken_info1(self):
        self.flags(ram_weight_multiplier=1.0)
        cost_cls = self.class_map['RamCost']()
        host1 = fakes.FakeHostState('host1', 'node1', {})
        host2 = fakes.FakeHostState('host2', 'node2', {})
        hosts = [host1, host2]
        instance_uuids = None
        request_spec = {'instance_type': 'fake_type',
                        'instance_uuids': instance_uuids,
                        'num_instances': 2}
        filter_properties = {'context': self.context.elevated()}

        cost_matrix = cost_cls.get_cost_matrix(hosts, instance_uuids,
                                            request_spec, filter_properties)

        ref_cost_matrix = [[host1.free_ram_mb * 1.0, host1.free_ram_mb * 1.0],
                           [host2.free_ram_mb * 1.0, host2.free_ram_mb * 1.0]]
        self.assertEqual(cost_matrix, ref_cost_matrix)

    def test_get_cost_matrix_broken_info2(self):
        self.flags(ram_weight_multiplier=1.0)
        cost_cls = self.class_map['RamCost']()
        host1 = fakes.FakeHostState('host1', 'node1', {})
        host2 = fakes.FakeHostState('host2', 'node2', {})
        hosts = [host1, host2]
        instance_uuids = None
        request_spec = {'instance_type': 'fake_type',
                        'instance_uuids': instance_uuids}
        filter_properties = {'context': self.context.elevated()}

        cost_matrix = cost_cls.get_cost_matrix(hosts, instance_uuids,
                                            request_spec, filter_properties)

        ref_cost_matrix = [[host1.free_ram_mb * 1.0],
                           [host2.free_ram_mb * 1.0]]
        self.assertEqual(cost_matrix, ref_cost_matrix)

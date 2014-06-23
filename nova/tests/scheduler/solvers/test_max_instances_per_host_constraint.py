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
Tests for solver scheduler Max_Instance_Per_Host linearconstraint.
"""

from nova.tests.scheduler import fakes
from nova.tests.scheduler.solvers import test_linearconstraints as lctest


class MaxInstancesPerHostConstraintTestCase(lctest.LinearConstraintsTestBase):
    """Test case for MaxInstancesPerHostsConstraint."""

    def setUp(self):
        super(MaxInstancesPerHostConstraintTestCase, self).setUp()

    def test_get_coefficient_vectors(self):
        variables = [[1, 2],
                    [3, 4]]
        host1 = fakes.FakeHostState('host1', 'node1',
                                    {'service': {'disabled': False}})
        host2 = fakes.FakeHostState('host2', 'node2',
                                    {'service': {'disabled': True}})
        hosts = [host1, host2]
        fake_instance1_uuid = 'fake-instance1-id'
        fake_instance2_uuid = 'fake-instance2-id'
        instance_uuids = [fake_instance1_uuid, fake_instance2_uuid]
        request_spec = {'instance_type': 'fake_type',
                        'instance_uuids': instance_uuids,
                        'num_instances': 2}
        filter_properties = {'context': self.context.elevated(),
                             'scheduler_hints': {'max_instances_per_host': 1}}
        constraint_cls = self.class_map['MaxInstancesPerHostConstraint'](
            variables, hosts, instance_uuids, request_spec, filter_properties)

        coeff_vectors = constraint_cls.get_coefficient_vectors(variables,
                        hosts, instance_uuids, request_spec, filter_properties)
        ref_coeff_vectors = [[1, 1, -1],
                            [1, 1, -1]]
        self.assertEqual(coeff_vectors, ref_coeff_vectors)

    def test_get_variable_vectors(self):
        variables = [[1, 2],
                    [3, 4]]
        host1 = fakes.FakeHostState('host1', 'node1',
                                    {'service': {'disabled': False}})
        host2 = fakes.FakeHostState('host2', 'node2',
                                    {'service': {'disabled': True}})
        hosts = [host1, host2]
        fake_instance1_uuid = 'fake-instance1-id'
        fake_instance2_uuid = 'fake-instance2-id'
        instance_uuids = [fake_instance1_uuid, fake_instance2_uuid]
        request_spec = {'instance_type': 'fake_type',
                        'instance_uuids': instance_uuids,
                        'num_instances': 2}
        filter_properties = {'context': self.context.elevated(),
                             'scheduler_hints': {'max_instances_per_host': 1}}
        constraint_cls = self.class_map['MaxInstancesPerHostConstraint'](
            variables, hosts, instance_uuids, request_spec, filter_properties)

        variable_vectors = constraint_cls.get_variable_vectors(variables,
            hosts, instance_uuids, request_spec, filter_properties)

        ref_variable_vectors = [[1, 2, 1],
                                [3, 4, 1]]
        self.assertEqual(variable_vectors, ref_variable_vectors)

    def test_get_operations(self):
        variables = [[1, 2],
                    [3, 4]]
        host1 = fakes.FakeHostState('host1', 'node1',
                                    {'service': {'disabled': False}})
        host2 = fakes.FakeHostState('host2', 'node2',
                                    {'service': {'disabled': True}})
        hosts = [host1, host2]
        fake_instance1_uuid = 'fake-instance1-id'
        fake_instance2_uuid = 'fake-instance2-id'
        instance_uuids = [fake_instance1_uuid, fake_instance2_uuid]
        request_spec = {'instance_type': 'fake_type',
                        'instance_uuids': instance_uuids,
                        'num_instances': 2}
        filter_properties = {'context': self.context.elevated(),
                             'scheduler_hints': {'max_instances_per_host': 1}}
        constraint_cls = self.class_map['MaxInstancesPerHostConstraint'](
            variables, hosts, instance_uuids, request_spec, filter_properties)

        operations = constraint_cls.get_operations(variables,
            hosts, instance_uuids, request_spec, filter_properties)

        ref_operations = [(lambda x: x == 0), (lambda x: x == 0)]
        self.assertEqual(len(operations), len(ref_operations))
        for idx in range(len(operations)):
            for n in range(4):
                self.assertEqual(operations[idx](n), ref_operations[idx](n))

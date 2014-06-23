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
Tests for solver scheduler linearconstraints.
"""

from nova import context
from nova.scheduler.solvers import linearconstraints
from nova import test
from nova.tests.scheduler import fakes


class LinearConstraintsTestBase(test.TestCase):
    """Base test case for linearconstraints."""
    def setUp(self):
        super(LinearConstraintsTestBase, self).setUp()
        self.context = context.RequestContext('fake', 'fake')
        linearconstraint_handler = linearconstraints.LinearConstraintHandler()
        classes = linearconstraint_handler.get_matching_classes(
                    ['nova.scheduler.solvers.linearconstraints.'
                    'all_linear_constraints'])
        self.class_map = {}
        for cls in classes:
            self.class_map[cls.__name__] = cls


class AllConstraintsTestCase(LinearConstraintsTestBase):
    """Test case for existence of all constraint classes."""
    def test_all_constraints(self):
        self.assertIn('AllHostsConstraint', self.class_map)


class AllHostsConstraintTestCase(LinearConstraintsTestBase):
    """Test case for AllHostsConstraint."""

    def test_get_coefficient_vectors(self):
        variables = [[1, 2],
                    [3, 4]]
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
        constraint_cls = self.class_map['AllHostsConstraint'](
            variables, hosts, instance_uuids, request_spec, filter_properties)

        coeff_vectors = constraint_cls.get_coefficient_vectors(variables,
            hosts, instance_uuids, request_spec, filter_properties)

        ref_coeff_vectors = [[0, 0],
                            [0, 0]]
        self.assertEqual(coeff_vectors, ref_coeff_vectors)

    def test_get_variable_vectors(self):
        variables = [[1, 2],
                    [3, 4]]
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
        constraint_cls = self.class_map['AllHostsConstraint'](
            variables, hosts, instance_uuids, request_spec, filter_properties)

        variable_vectors = constraint_cls.get_variable_vectors(variables,
            hosts, instance_uuids, request_spec, filter_properties)

        ref_variable_vectors = [[1, 2],
                                [3, 4]]
        self.assertEqual(variable_vectors, ref_variable_vectors)

    def test_get_operations(self):
        variables = [[1, 2],
                    [3, 4]]
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
        constraint_cls = self.class_map['AllHostsConstraint'](
            variables, hosts, instance_uuids, request_spec, filter_properties)

        operations = constraint_cls.get_operations(variables,
            hosts, instance_uuids, request_spec, filter_properties)

        ref_operations = [(lambda x: x == 0), (lambda x: x == 0)]
        self.assertEqual(len(operations), len(ref_operations))
        for idx in range(len(operations)):
            for n in range(4):
                self.assertEqual(operations[idx](n), ref_operations[idx](n))

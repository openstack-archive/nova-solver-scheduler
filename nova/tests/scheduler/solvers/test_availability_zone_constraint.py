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
Tests for solver scheduler Availability Zone linearconstraint.
"""

import mock

from nova import db
from nova.tests.scheduler import fakes
from nova.tests.scheduler.solvers import test_linearconstraints as lctests

HOSTS = [fakes.FakeHostState('host1', 'node1',
          {'free_disk_mb': 11 * 1024, 'total_usable_disk_gb': 13,
           'free_ram_mb': 1024, 'total_usable_ram_mb': 1024,
           'vcpus_total': 4, 'vcpus_used': 7,
           'service': {'disabled': False}}),
         fakes.FakeHostState('host2', 'node2',
          {'free_disk_mb': 1024, 'total_usable_disk_gb': 13,
           'free_ram_mb': 1023, 'total_usable_ram_mb': 1024,
           'vcpus_total': 4, 'vcpus_used': 8,
           'service': {'disabled': False}}),
        ]

INSTANCE_UUIDS = ['fake-instance1-uuid', 'fake-instance2-uuid']

INSTANCE_TYPES = [{'root_gb': 1, 'ephemeral_gb': 1, 'swap': 512,
                   'memory_mb': 1024, 'vcpus': 1},
                 ]

REQUEST_SPECS = [{'instance_type': INSTANCE_TYPES[0],
                  'instance_uuids': INSTANCE_UUIDS,
                  'instance_properties': {'availability_zone': 'zone1'},
                  'num_instances': 2},
                 {'instance_type': INSTANCE_TYPES[0],
                  'instance_uuids': INSTANCE_UUIDS,
                  'instance_properties': {'availability_zone': 'default'},
                  'num_instances': 2},
                 {'instance_type': INSTANCE_TYPES[0],
                  'instance_uuids': INSTANCE_UUIDS,
                  'instance_properties': {'availability_zone': 'unknown'},
                  'num_instances': 2},
                 {'instance_type': INSTANCE_TYPES[0],
                  'instance_uuids': INSTANCE_UUIDS,
                  'num_instances': 2},
                ]


class AvailabilityZoneConstraintTestCase(lctests.LinearConstraintsTestBase):
    """Test case for AvailabilityZoneConstraint."""

    def setUp(self):
        super(AvailabilityZoneConstraintTestCase, self).setUp()
        self.variables = [[1, 2],
                          [3, 4]]
        self.hosts = HOSTS
        self.instance_uuids = INSTANCE_UUIDS
        self.instance_type = INSTANCE_TYPES[0].copy()
        self.request_spec = REQUEST_SPECS[0].copy()
        self.filter_properties = {'context': self.context.elevated(),
                                  'instance_type': self.instance_type}

    def test_get_coefficient_vectors_in_metadata(self):

        def dbget_side_effect(*args, **kwargs):
            if args[1] == 'host1':
                return {'availability_zone': 'zone1'}
            else:
                return {}

        constraint_cls = self.class_map['AvailabilityZoneConstraint'](
            self.variables, self.hosts, self.instance_uuids,
            self.request_spec, self.filter_properties)

        with mock.patch.object(db, 'aggregate_metadata_get_by_host') as dbget:
            dbget.side_effect = dbget_side_effect
            coeff_vectors = constraint_cls.get_coefficient_vectors(
                                self.variables, self.hosts,
                                self.instance_uuids, self.request_spec,
                                self.filter_properties)
            ref_coeff_vectors = [[0, 0],
                                 [1, 1]]
            self.assertEqual(ref_coeff_vectors, coeff_vectors)

    def test_get_coefficient_vectors_in_default_zone(self):
        self.request_spec = REQUEST_SPECS[1].copy()
        self.flags(default_availability_zone='default')
        constraint_cls = self.class_map['AvailabilityZoneConstraint'](
            self.variables, self.hosts, self.instance_uuids,
            self.request_spec, self.filter_properties)

        with mock.patch.object(db, 'aggregate_metadata_get_by_host') as dbget:
            dbget.return_value = {}
            coeff_vectors = constraint_cls.get_coefficient_vectors(
                                self.variables, self.hosts,
                                self.instance_uuids, self.request_spec,
                                self.filter_properties)
            ref_coeff_vectors = [[0, 0],
                                 [0, 0]]
            self.assertEqual(ref_coeff_vectors, coeff_vectors)

    def test_get_coefficient_vectors_in_non_default_zone(self):
        self.request_spec = REQUEST_SPECS[2].copy()
        self.flags(default_availability_zone='default')
        constraint_cls = self.class_map['AvailabilityZoneConstraint'](
            self.variables, self.hosts, self.instance_uuids,
            self.request_spec, self.filter_properties)

        with mock.patch.object(db, 'aggregate_metadata_get_by_host') as dbget:
            dbget.return_value = {}
            coeff_vectors = constraint_cls.get_coefficient_vectors(
                                self.variables, self.hosts,
                                self.instance_uuids, self.request_spec,
                                self.filter_properties)
            ref_coeff_vectors = [[1, 1],
                                 [1, 1]]
            self.assertEqual(ref_coeff_vectors, coeff_vectors)

    def test_get_coefficient_vectors_missing_zone(self):
        self.request_spec = REQUEST_SPECS[3].copy()
        constraint_cls = self.class_map['AvailabilityZoneConstraint'](
            self.variables, self.hosts, self.instance_uuids,
            self.request_spec, self.filter_properties)

        coeff_vectors = constraint_cls.get_coefficient_vectors(self.variables,
                                           self.hosts, self.instance_uuids,
                                           self.request_spec,
                                           self.filter_properties)
        ref_coeff_vectors = [[0, 0],
                             [0, 0]]
        self.assertEqual(ref_coeff_vectors, coeff_vectors)

    def test_get_variable_vectors(self):
        constraint_cls = self.class_map['AvailabilityZoneConstraint'](
            self.variables, self.hosts, self.instance_uuids,
            self.request_spec, self.filter_properties)

        variable_vectors = constraint_cls.get_variable_vectors(self.variables,
            self.hosts, self.instance_uuids, self.request_spec,
            self.filter_properties)

        ref_variable_vectors = [[1, 2],
                                [3, 4]]
        self.assertEqual(variable_vectors, ref_variable_vectors)

    def test_get_operations(self):
        constraint_cls = self.class_map['AvailabilityZoneConstraint'](
            self.variables, self.hosts, self.instance_uuids,
            self.request_spec, self.filter_properties)

        operations = constraint_cls.get_operations(self.variables, self.hosts,
            self.instance_uuids, self.request_spec, self.filter_properties)

        ref_operations = [(lambda x: x == 0), (lambda x: x == 0)]
        self.assertEqual(len(operations), len(ref_operations))
        for idx in range(len(operations)):
            for n in range(4):
                self.assertEqual(operations[idx](n), ref_operations[idx](n))

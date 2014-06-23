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
Tests for Volume Affinity Cost.
"""

import mock

from cinderclient import exceptions as client_exceptions

from nova.tests.scheduler import fakes
from nova.tests.scheduler.solvers import test_costs as tc
from nova.tests.volume import test_cinder as cindertest
import nova.volume.cinder as volumecinder


class FakeVolume(object):

    def __init__(self, id, host_id):
        setattr(self, 'os-vol-host-attr:host', host_id)
        self.id = id


HOSTS = [fakes.FakeHostState('host1', 'node1', {}),
         fakes.FakeHostState('host2', 'node2', {}),
        ]

VOLUMES = [FakeVolume('volume1', 'host1'),
           FakeVolume('volume2', 'host2'),
          ]

INSTANCE_UUIDS = ['fake-instance-uuid', 'fake-instance2-uuid']


class VolumeAffinityCostTestCase(tc.CostsTestBase):
    """Test case for VolumeAffinityCost."""

    def setUp(self):
        super(VolumeAffinityCostTestCase, self).setUp()
        self.cinderclient = cindertest.FakeCinderClient()

    def test_get_cost_matrix_single(self):
        cost_cls = self.class_map['VolumeAffinityCost']()
        hosts = HOSTS[0:1]
        instance_uuids = INSTANCE_UUIDS[0:1]
        request_spec = {'instance_type': 'fake_type',
                        'instance_uuids': instance_uuids}
        filter_properties = {'context': self.context.elevated(),
                             'scheduler_hints': {
                                 'affinity_volume_id': 'volume1'}}
        with mock.patch.object(volumecinder, 'cinderclient') as client_mock:
            client_mock.return_value = self.cinderclient
            with mock.patch.object(self.cinderclient.volumes,
                                   'get') as get_mock:
                get_mock.return_value = VOLUMES[0]
                cost_matrix = cost_cls.get_cost_matrix(hosts, instance_uuids,
                                                       request_spec,
                                                       filter_properties)
                ref_cost_matrix = [[0]]
                self.assertEqual(cost_matrix, ref_cost_matrix)

    def test_get_cost_matrix_multi(self):
        cost_cls = self.class_map['VolumeAffinityCost']()
        hosts = HOSTS
        instance_uuids = INSTANCE_UUIDS
        request_spec = {'instance_type': 'fake_type',
                        'instance_uuids': instance_uuids,
                        'num_instances': 2}
        filter_properties = {'context': self.context.elevated(),
                             'scheduler_hints': {
                                 'affinity_volume_id': 'volume1'}}
        context = filter_properties.get('context')
        with mock.patch.object(volumecinder, 'cinderclient') as client_mock:
            client_mock.return_value = self.cinderclient
            with mock.patch.object(self.cinderclient.volumes,
                                   'get') as get_mock:
                get_mock.return_value = VOLUMES[0]
                cost_matrix = cost_cls.get_cost_matrix(hosts, instance_uuids,
                                                       request_spec,
                                                       filter_properties)
                ref_cost_matrix = [[0, 0],
                                   [1, 1]]
                self.assertEqual(cost_matrix, ref_cost_matrix)

    def test_get_cost_matrix_multi_missing_hint(self):
        cost_cls = self.class_map['VolumeAffinityCost']()
        hosts = HOSTS
        instance_uuids = INSTANCE_UUIDS
        request_spec = {'instance_type': 'fake_type',
                        'instance_uuids': instance_uuids,
                        'num_instances': 2}
        filter_properties = {'context': self.context.elevated()}
        cost_matrix = cost_cls.get_cost_matrix(hosts, instance_uuids,
                                               request_spec,
                                               filter_properties)
        ref_cost_matrix = [[1, 1],
                           [1, 1]]
        self.assertEqual(cost_matrix, ref_cost_matrix)

    def test_get_cost_matrix_multi_unknown_volume_id(self):

        def mock_side_effect(*args, **kwargs):
            raise client_exceptions.NotFound(None)

        cost_cls = self.class_map['VolumeAffinityCost']()
        hosts = HOSTS
        instance_uuids = INSTANCE_UUIDS
        request_spec = {'instance_type': 'fake_type',
                        'instance_uuids': instance_uuids,
                        'num_instances': 2}
        filter_properties = {'context': self.context.elevated(),
                             'scheduler_hints': {
                                 'affinity_volume_id': 'volume234'}}
        context = filter_properties.get('context')
        with mock.patch.object(volumecinder, 'cinderclient') as client_mock:
            client_mock.return_value = self.cinderclient
            with mock.patch.object(self.cinderclient.volumes,
                                   'get') as get_mock:
                get_mock.side_effect = mock_side_effect
                cost_matrix = cost_cls.get_cost_matrix(hosts, instance_uuids,
                                                       request_spec,
                                                       filter_properties)
                ref_cost_matrix = [[1, 1],
                                   [1, 1]]
                self.assertEqual(cost_matrix, ref_cost_matrix)

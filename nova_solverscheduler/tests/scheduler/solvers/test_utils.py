# Copyright 2015 Cisco Systems, Inc.
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
import os.path
import tempfile

from oslo_config import cfg

from nova import objects
from nova import test
from nova_solverscheduler.scheduler.solvers import utils
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes

CONF = cfg.CONF

_AGGREGATE_FIXTURES = [
    objects.Aggregate(
        id=1,
        name='aggr1',
        hosts=['fake-host'],
        metadata={'k1': '1', 'k2': '2'},
    ),
    objects.Aggregate(
        id=2,
        name='bar',
        hosts=['fake-host'],
        metadata={'k1': '3', 'k2': '4'},
    ),
    objects.Aggregate(
        id=3,
        name='bar',
        hosts=['fake-host'],
        metadata={'k1': '6,7', 'k2': '8, 9'},
    ),
]


class TestRackConfigLoader(test.NoDBTestCase):
    """Test case for rack config file loading."""

    _rack_config = '''
[ml2_mech_cisco_nexus:1.1.1.1]
compute1=1/1
compute2=1/2
[other-section]
k=bla
    '''

    def setUp(self):
        super(TestRackConfigLoader, self).setUp()
        self.config = tempfile.NamedTemporaryFile(mode="w+t")
        self.config.write(self._rack_config.lstrip())
        self.config.seek(0)
        self.config.flush()

        self.config_path = None
        if not os.path.isabs(self.config.name):
            self.config_path = CONF.find_file(self.config.name)
        elif os.path.exists(self.config.name):
            self.config_path = self.config.name

    def test_load_rack_config_happy_day(self):
        self.flags(rack_config=self.config_path,
                    rack_config_prefix='ml2_mech_cisco_nexus')
        rackcfg = utils.get_host_racks_config()

        ref_rackcfg = {
            'compute1': set(['ml2_mech_cisco_nexus:1.1.1.1']),
            'compute2': set(['ml2_mech_cisco_nexus:1.1.1.1'])
        }
        self.assertEqual(ref_rackcfg, rackcfg)

    def test_load_rack_config_no_found(self):
        self.flags(rack_config='non_existing_file')
        rackcfg = utils.get_host_racks_config()
        self.assertEqual({}, rackcfg)

    def tearDown(self):
        self.config.close()
        super(TestRackConfigLoader, self).tearDown()


class TestGetHostRacksMap(test.NoDBTestCase):
    def setUp(self):
        super(TestGetHostRacksMap, self).setUp()
        self.fake_aggregates = [
            objects.Aggregate(
                id=1,
                name='aggr1',
                hosts=['host1', 'host2'],
                metadata={'rack': 'rack1', 'foo': 'bar'},
            ),
            objects.Aggregate(
                id=2,
                name='aggr2',
                hosts=['host2'],
                metadata={'rack': 'rack2'},
            ),
            objects.Aggregate(
                id=3,
                name='aggr3',
                hosts=['host3'],
                metadata={'foo': 'bar'},
            ),
        ]

    def test_get_host_racks_map_from_aggregate(self):
        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1',
                {'aggregates': self.fake_aggregates[0:1]})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node2',
                {'aggregates': self.fake_aggregates[0:2]})
        host3 = fakes.FakeSolverSchedulerHostState('host3', 'node3',
                {'aggregates': self.fake_aggregates[2:3]})
        host4 = fakes.FakeSolverSchedulerHostState('host4', 'node4',
                {'aggregates': []})
        hosts = [host1, host2, host3, host4]

        result = utils.get_host_racks_map(hosts)
        expected_result = {
            'host1': set(['rack1']),
            'host2': set(['rack1', 'rack2'])
        }

        self.assertEqual(expected_result, result)

    @mock.patch('nova_solverscheduler.scheduler.solvers.utils.'
                'get_host_racks_config')
    def test_get_host_racks_map_no_aggregate_key(self, getconfig_mock):
        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1', {})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node2', {})
        host3 = fakes.FakeSolverSchedulerHostState('host3', 'node3',
                {'aggregates': self.fake_aggregates[2:3]})
        host4 = fakes.FakeSolverSchedulerHostState('host4', 'node4', {})
        hosts = [host1, host2, host3, host4]

        expected_result = {'host1': set('rack1'), 'host2': set('rack1')}
        getconfig_mock.return_value = expected_result

        result = utils.get_host_racks_map(hosts)

        self.assertEqual(expected_result, result)

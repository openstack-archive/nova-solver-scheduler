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

import os.path
import tempfile

from oslo.config import cfg

from nova import context
from nova import db
from nova import exception
from nova import test
from nova_solverscheduler.scheduler.solvers import utils
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes

CONF = cfg.CONF


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


class TestGetInstanceHosts(test.NoDBTestCase):
    USES_DB = True

    def setUp(self):
        super(TestGetInstanceHosts, self).setUp()
        self.context = context.RequestContext('fake_usr', 'fake_proj')
        instance1 = fakes.FakeInstance(
                context=self.context,
                params={'host': 'host1',
                        'user_id': self.context.user_id,
                        'project_id': self.context.project_id})
        instance2 = fakes.FakeInstance(
                context=self.context,
                params={'host': 'host2',
                        'user_id': self.context.user_id,
                        'project_id': self.context.project_id})
        instance3 = fakes.FakeInstance(
                context=self.context,
                params={'user_id': self.context.user_id,
                        'project_id': self.context.project_id})
        inst_uuid_1 = instance1.uuid
        inst_uuid_2 = instance2.uuid
        inst_uuid_3 = instance3.uuid
        self.fake_instance_uuids = [inst_uuid_1, inst_uuid_2, inst_uuid_3]

    def test_get_hosts_from_instance_uuids_normal(self):
        fake_uuids = self.fake_instance_uuids[0:1]
        hosts = utils.get_hosts_from_instance_uuids(self.context, fake_uuids)
        expected_hosts = ['host1']
        self.assertTrue(isinstance(hosts, list))
        self.assertEqual(set(expected_hosts), set(hosts))

        fake_uuids = self.fake_instance_uuids[0:2]
        hosts = utils.get_hosts_from_instance_uuids(self.context, fake_uuids)
        expected_hosts = ['host1', 'host2']
        self.assertTrue(isinstance(hosts, list))
        self.assertEqual(set(expected_hosts), set(hosts))

    def test_get_hosts_from_instance_uuids_missing_host(self):
        fake_uuids = self.fake_instance_uuids
        self.assertRaises(ValueError, utils.get_hosts_from_instance_uuids,
                          self.context, fake_uuids)

    def test_get_hosts_from_instance_uuids_wrong_uuid(self):
        fake_uuids = self.fake_instance_uuids[0:2] + ['unknown_uuid']
        self.assertRaises(exception.InstanceNotFound,
                          utils.get_hosts_from_instance_uuids,
                          self.context, fake_uuids)

        fake_uuids = ['unknown_uuid']
        self.assertRaises(exception.InstanceNotFound,
                          utils.get_hosts_from_instance_uuids,
                          self.context, fake_uuids)

        fake_uuids = []
        hosts = utils.get_hosts_from_instance_uuids(self.context, fake_uuids)
        expected_hosts = []
        self.assertEqual(set(expected_hosts), set(hosts))


class TestGetServerGroupHosts(test.NoDBTestCase):
    USES_DB = True

    def setUp(self):
        super(TestGetServerGroupHosts, self).setUp()
        self.context = context.RequestContext('fake_usr', 'fake_proj')
        instance1 = fakes.FakeInstance(
                context=self.context,
                params={'host': 'host1',
                        'user_id': self.context.user_id,
                        'project_id': self.context.project_id})
        inst_uuid_1 = instance1.uuid
        self.fake_instance_uuids = [inst_uuid_1]

        group1 = db.instance_group_create(
                self.context,
                {'name': 'ig1',
                 'user_id': self.context.user_id,
                 'project_id': self.context.project_id},
                policies=['affinity'],
                members=[inst_uuid_1])
        group2 = db.instance_group_create(
                self.context,
                {'name': 'ig2',
                 'user_id': self.context.user_id,
                 'project_id': self.context.project_id},
                policies=['anti-affinity'])
        group3 = db.instance_group_create(
                self.context,
                {'name': 'ig3',
                 'user_id': self.context.user_id,
                 'project_id': self.context.project_id},
                policies=['anti-affinity'],
                members=['unkown_uuid'])
        self.fake_group_uuids = [group1['uuid'],
                                 group2['uuid'],
                                 group3['uuid']]
        self.fake_group_names = [group1['name'],
                                 group2['name'],
                                 group3['name']]

    def test_get_hosts_from_group_hint_normal(self):
        fake_uuid = self.fake_group_uuids[0]
        hosts = utils.get_hosts_from_group_hint(self.context, fake_uuid)
        expected_hosts = ['host1']
        self.assertTrue(isinstance(hosts, list))
        self.assertEqual(set(expected_hosts), set(hosts))

        fake_name = self.fake_group_names[0]
        hosts = utils.get_hosts_from_group_hint(self.context, fake_name)
        expected_hosts = ['host1']
        self.assertTrue(isinstance(hosts, list))
        self.assertEqual(set(expected_hosts), set(hosts))

        fake_uuid = self.fake_group_uuids[1]
        hosts = utils.get_hosts_from_group_hint(self.context, fake_uuid)
        expected_hosts = []
        self.assertTrue(isinstance(hosts, list))
        self.assertEqual(set(expected_hosts), set(hosts))

    def test_get_hosts_from_group_hint_wronghint(self):
        fake_name = 'unknown_name'
        self.assertRaises(exception.InstanceGroupNotFound,
                          utils.get_hosts_from_group_hint,
                          self.context, fake_name)

    def test_get_hosts_from_group_hint_wrongmember(self):
        fake_uuid = self.fake_group_uuids[2]
        self.assertRaises(exception.InstanceNotFound,
                          utils.get_hosts_from_group_hint,
                          self.context, fake_uuid)

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

from nova import test
from nova_solverscheduler.scheduler.solvers import utils

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

# Copyright (c) 2011 OpenStack Foundation
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
Tests For SolverSchedulerHostManager
"""
from nova.openstack.common import timeutils
from nova import test
from nova_solverscheduler.scheduler import solver_scheduler_host_manager \
        as host_manager


class SolverSchedulerHostManagerTestCase(test.NoDBTestCase):
    """Test case for HostManager class."""

    def setUp(self):
        super(SolverSchedulerHostManagerTestCase, self).setUp()
        self.host_manager = host_manager.SolverSchedulerHostManager()
        self.fake_hosts = [host_manager.SolverSchedulerHostState(
                'fake_host%s' % x, 'fake-node') for x in xrange(1, 5)]
        self.fake_hosts += [host_manager.SolverSchedulerHostState(
                'fake_multihost', 'fake-node%s' % x) for x in xrange(1, 5)]
        self.addCleanup(timeutils.clear_time_override)

    def _verify_result(self, info, result):
        self.assertEqual(set(info['expected_objs']), set(result))

    def test_get_hosts_with_ignore(self):
        fake_properties = {'ignore_hosts': ['fake_host1', 'fake_host3',
                'fake_host5', 'fake_multihost']}

        # [1] and [3] are host2 and host4
        info = {'expected_objs': [self.fake_hosts[1], self.fake_hosts[3]],
                'expected_fprops': fake_properties}

        result = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                            self.fake_hosts, fake_properties)
        self._verify_result(info, result)

    def test_get_hosts_with_force(self):
        fake_properties = {'force_hosts': ['fake_host1', 'fake_host3',
                'fake_host5']}

        # [0] and [2] are host1 and host3
        info = {'expected_objs': [self.fake_hosts[0], self.fake_hosts[2]],
                'expected_fprops': fake_properties,
                'got_fprops': []}

        result = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                            self.fake_hosts, fake_properties)
        self._verify_result(info, result)

    def test_get_hosts_with_no_matching_force_hosts(self):
        fake_properties = {'force_hosts': ['fake_host5', 'fake_host6']}

        info = {'expected_objs': [],
                'expected_fprops': fake_properties,
                'got_fprops': []}

        result = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                            self.fake_hosts, fake_properties)
        self._verify_result(info, result)

    def test_get_hosts_with_ignore_and_force_hosts(self):
        # Ensure ignore_hosts processed before force_hosts in host filters.
        fake_properties = {'force_hosts': ['fake_host3', 'fake_host1'],
                           'ignore_hosts': ['fake_host1']}

        # only fake_host3 should be left.
        info = {'expected_objs': [self.fake_hosts[2]],
                'expected_fprops': fake_properties,
                'got_fprops': []}

        result = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                            self.fake_hosts, fake_properties)
        self._verify_result(info, result)

    def test_get_hosts_with_force_host_and_many_nodes(self):
        # Ensure all nodes returned for a host with many nodes
        fake_properties = {'force_hosts': ['fake_multihost']}

        info = {'expected_objs': [self.fake_hosts[4], self.fake_hosts[5],
                                  self.fake_hosts[6], self.fake_hosts[7]],
                'expected_fprops': fake_properties,
                'got_fprops': []}

        result = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                            self.fake_hosts, fake_properties)
        self._verify_result(info, result)

    def test_get_hosts_with_force_nodes(self):
        fake_properties = {'force_nodes': ['fake-node2', 'fake-node4',
                                           'fake-node9']}

        # [5] is fake-node2, [7] is fake-node4
        info = {'expected_objs': [self.fake_hosts[5], self.fake_hosts[7]],
                'expected_fprops': fake_properties,
                'got_fprops': []}

        result = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                            self.fake_hosts, fake_properties)
        self._verify_result(info, result)

    def test_get_hosts_with_force_hosts_and_nodes(self):
        # Ensure only overlapping results if both force host and node
        fake_properties = {'force_hosts': ['fake_host1', 'fake_multihost'],
                           'force_nodes': ['fake-node2', 'fake-node9']}

        # [5] is fake-node2
        info = {'expected_objs': [self.fake_hosts[5]],
                'expected_fprops': fake_properties,
                'got_fprops': []}

        result = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                            self.fake_hosts, fake_properties)
        self._verify_result(info, result)

    def test_get_hosts_with_force_hosts_and_wrong_nodes(self):
        # Ensure non-overlapping force_node and force_host yield no result
        fake_properties = {'force_hosts': ['fake_multihost'],
                           'force_nodes': ['fake-node']}

        info = {'expected_objs': [],
                'expected_fprops': fake_properties,
                'got_fprops': []}

        result = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                            self.fake_hosts, fake_properties)
        self._verify_result(info, result)

    def test_get_hosts_with_ignore_hosts_and_force_nodes(self):
        # Ensure ignore_hosts can coexist with force_nodes
        fake_properties = {'force_nodes': ['fake-node4', 'fake-node2'],
                           'ignore_hosts': ['fake_host1', 'fake_host2']}

        info = {'expected_objs': [self.fake_hosts[5], self.fake_hosts[7]],
                'expected_fprops': fake_properties,
                'got_fprops': []}

        result = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                            self.fake_hosts, fake_properties)
        self._verify_result(info, result)

    def test_get_hosts_with_ignore_hosts_and_force_same_nodes(self):
        # Ensure ignore_hosts is processed before force_nodes
        fake_properties = {'force_nodes': ['fake_node4', 'fake_node2'],
                           'ignore_hosts': ['fake_multihost']}

        info = {'expected_objs': [],
                'expected_fprops': fake_properties,
                'got_fprops': []}

        result = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                            self.fake_hosts, fake_properties)
        self._verify_result(info, result)

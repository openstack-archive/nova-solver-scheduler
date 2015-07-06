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

import mock

from nova import context
from nova import test
from nova_solverscheduler.scheduler.solvers.constraints import aggregate_disk
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes


class TestAggregateDiskConstraint(test.NoDBTestCase):
    def setUp(self):
        super(TestAggregateDiskConstraint, self).setUp()
        self.constraint_cls = aggregate_disk.AggregateDiskConstraint
        self.context = context.RequestContext('fake', 'fake')
        self._generate_fake_constraint_input()

    def _generate_fake_constraint_input(self):
        self.fake_filter_properties = {
                'context': self.context,
                'instance_type': {'root_gb': 1, 'ephemeral_gb': 1, 'swap': 0},
                'instance_uuids': ['fake_uuid_%s' % x for x in range(2)],
                'num_instances': 2}
        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1',
                {'free_disk_mb': 1024, 'total_usable_disk_gb': 2})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node1',
                {'free_disk_mb': 1024, 'total_usable_disk_gb': 2})
        host3 = fakes.FakeSolverSchedulerHostState('host3', 'node1',
                {'free_disk_mb': 1024, 'total_usable_disk_gb': 2})
        self.fake_hosts = [host1, host2, host3]

    @mock.patch('nova_solverscheduler.scheduler.solvers.utils.'
                'aggregate_values_from_key')
    def test_get_constraint_matrix(self, agg_mock):
        self.flags(disk_allocation_ratio=1.0)

        def _agg_mock_side_effect(*args, **kwargs):
            if args[0].host == 'host1':
                return set(['2.0', '3.0'])
            if args[0].host == 'host2':
                return set(['3.0'])
            if args[0].host == 'host3':
                return set([])
        agg_mock.side_effect = _agg_mock_side_effect

        expected_cons_mat = [
            [True, False],
            [True, True],
            [False, False]]
        cons_mat = self.constraint_cls().get_constraint_matrix(
                    self.fake_hosts, self.fake_filter_properties)
        agg_mock.assert_any_call(self.fake_hosts[0], 'disk_allocation_ratio')
        agg_mock.assert_any_call(self.fake_hosts[1], 'disk_allocation_ratio')
        agg_mock.assert_any_call(self.fake_hosts[2], 'disk_allocation_ratio')
        self.assertEqual(expected_cons_mat, cons_mat)

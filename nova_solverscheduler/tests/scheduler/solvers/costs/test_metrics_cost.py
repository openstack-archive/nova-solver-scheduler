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

"""Test case for solver scheduler RAM cost."""

from nova import context
from nova.scheduler import host_manager
from nova import test
from nova_solverscheduler.scheduler.solvers import costs
from nova_solverscheduler.scheduler.solvers.costs import ram_cost
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes


class TestMetricsCost(test.NoDBTestCase):
    def setUp(self):
        super(TestMetricsCost, self).setUp()
        self.context = context.RequestContext('fake_usr', 'fake_proj')
        self.cost_handler = costs.CostHandler()
        self.cost_classes = self.cost_handler.get_matching_classes(
                ['nova_solverscheduler.scheduler.solvers.costs.metrics_cost.'
                'MetricsCost'])

    def _get_all_hosts(self):
        def fake_metric(value):
            return host_manager.MetricItem(value=value, timestamp='fake-time',
                                           source='fake-source')

        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1',
                {'metrics': {'foo': fake_metric(512),
                            'bar': fake_metric(1)}})
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node2',
                {'metrics': {'foo': fake_metric(1024),
                            'bar': fake_metric(2)}})
        host3 = fakes.FakeSolverSchedulerHostState('host3', 'node3',
                {'metrics': {'foo': fake_metric(3072),
                            'bar': fake_metric(1)}})
        host4 = fakes.FakeSolverSchedulerHostState('host4', 'node4',
                {'metrics': {'foo': fake_metric(8192),
                            'bar': fake_metric(0)}})
        host5 = fakes.FakeSolverSchedulerHostState('host5', 'node5',
                {'metrics': {'foo': fake_metric(768),
                            'bar': fake_metric(0),
                            'zot': fake_metric(1)}})
        host6 = fakes.FakeSolverSchedulerHostState('host6', 'node6',
                {'metrics': {'foo': fake_metric(2048),
                            'bar': fake_metric(0),
                            'zot': fake_metric(2)}})
        return [host1, host2, host3, host4, host5, host6]

    def _get_fake_cost_inputs(self):
        fake_hosts = self._get_all_hosts()
        # FIXME: ideally should mock get_hosts_stripping_forced_and_ignored()
        fake_hosts = list(fake_hosts)
        # the hosts order may be arbitrary, here we manually order them
        # which is for convenience of testings
        tmp = []
        for i in range(len(fake_hosts)):
            for fh in fake_hosts:
                if fh.host == 'host%s' % (i + 1):
                    tmp.append(fh)
        fake_hosts = tmp
        fake_filter_properties = {
                'context': self.context.elevated(),
                'num_instances': 3,
                'instance_uuids': ['fake_uuid_%s' % x for x in range(3)]}
        return (fake_hosts, fake_filter_properties)

    def test_metrics_cost_multiplier_1(self):
        self.flags(ram_cost_multiplier=0.5, group='solver_scheduler')
        self.assertEqual(0.5, ram_cost.RamCost().cost_multiplier())

    def test_metrics_cost_multiplier_2(self):
        self.flags(ram_cost_multiplier=(-2), group='solver_scheduler')
        self.assertEqual((-2), ram_cost.RamCost().cost_multiplier())

    def test_get_extended_cost_matrix_single_resource(self):
        # host1: foo=512
        # host2: foo=1024
        # host3: foo=3072
        # host4: foo=8192
        setting = ['foo=1']
        self.flags(weight_setting=setting, group='metrics')

        fake_hosts, fake_filter_properties = self._get_fake_cost_inputs()
        fake_hosts = fake_hosts[0:4]

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [-0.0625, -0.0625, -0.0625, -0.0625],
                [-0.125, -0.125, -0.125, -0.125],
                [-0.375, -0.375, -0.375, -0.375],
                [-1.0, -1.0, -1.0, -1.0]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        expected_x_cost_mat = [[round(val, 4) for val in row]
                                for row in expected_x_cost_mat]
        x_cost_mat = [[round(val, 4) for val in row] for row in x_cost_mat]
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_multiple_resource(self):
        # host1: foo=512,  bar=1
        # host2: foo=1024, bar=2
        # host3: foo=3072, bar=1
        # host4: foo=8192, bar=0
        setting = ['foo=0.0001', 'bar=1']
        self.flags(weight_setting=setting, group='metrics')

        fake_hosts, fake_filter_properties = self._get_fake_cost_inputs()
        fake_hosts = fake_hosts[0:4]

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [-0.5, -0.5, -0.5, -0.5],
                [-1.0, -1.0, -1.0, -1.0],
                [-0.6218, -0.6218, -0.6218, -0.6218],
                [-0.3896, -0.3896, -0.3896, -0.3896]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        expected_x_cost_mat = [[round(val, 4) for val in row]
                                for row in expected_x_cost_mat]
        x_cost_mat = [[round(val, 4) for val in row] for row in x_cost_mat]
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_single_resource_negative_ratio(self):
        # host1: foo=512
        # host2: foo=1024
        # host3: foo=3072
        # host4: foo=8192
        setting = ['foo=-1']
        self.flags(weight_setting=setting, group='metrics')

        fake_hosts, fake_filter_properties = self._get_fake_cost_inputs()
        fake_hosts = fake_hosts[0:4]

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [0.0625, 0.0625, 0.0625, 0.0625],
                [0.125, 0.125, 0.125, 0.125],
                [0.375, 0.375, 0.375, 0.375],
                [1.0, 1.0, 1.0, 1.0]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        expected_x_cost_mat = [[round(val, 4) for val in row]
                                for row in expected_x_cost_mat]
        x_cost_mat = [[round(val, 4) for val in row] for row in x_cost_mat]
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_multiple_resource_missing_ratio(self):
        # host1: foo=512,  bar=1
        # host2: foo=1024, bar=2
        # host3: foo=3072, bar=1
        # host4: foo=8192, bar=0
        setting = ['foo=0.0001', 'bar']
        self.flags(weight_setting=setting, group='metrics')

        fake_hosts, fake_filter_properties = self._get_fake_cost_inputs()
        fake_hosts = fake_hosts[0:4]

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [-0.0625, -0.0625, -0.0625, -0.0625],
                [-0.125, -0.125, -0.125, -0.125],
                [-0.375, -0.375, -0.375, -0.375],
                [-1.0, -1.0, -1.0, -1.0]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        expected_x_cost_mat = [[round(val, 4) for val in row]
                                for row in expected_x_cost_mat]
        x_cost_mat = [[round(val, 4) for val in row] for row in x_cost_mat]
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_multiple_resource_wrong_ratio(self):
        # host1: foo=512,  bar=1
        # host2: foo=1024, bar=2
        # host3: foo=3072, bar=1
        # host4: foo=8192, bar=0
        setting = ['foo=0.0001', 'bar = 2.0t']
        self.flags(weight_setting=setting, group='metrics')

        fake_hosts, fake_filter_properties = self._get_fake_cost_inputs()
        fake_hosts = fake_hosts[0:4]

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [-0.0625, -0.0625, -0.0625, -0.0625],
                [-0.125, -0.125, -0.125, -0.125],
                [-0.375, -0.375, -0.375, -0.375],
                [-1.0, -1.0, -1.0, -1.0]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        expected_x_cost_mat = [[round(val, 4) for val in row]
                                for row in expected_x_cost_mat]
        x_cost_mat = [[round(val, 4) for val in row] for row in x_cost_mat]
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_metric_not_found(self):
        # host3: foo=3072, bar=1
        # host4: foo=8192, bar=0
        # host5: foo=768, bar=0, zot=1
        # host6: foo=2048, bar=0, zot=2
        setting = ['foo=0.0001', 'zot=-2']
        self.flags(weight_setting=setting, group='metrics')

        fake_hosts, fake_filter_properties = self._get_fake_cost_inputs()
        fake_hosts = fake_hosts[2:6]

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [1.0, 1.0, 1.0, 1.0],
                [1.0, 1.0, 1.0, 1.0],
                [0.3394, 0.3394, 0.3394, 0.3394],
                [0.6697, 0.6697, 0.6697, 0.6697]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        expected_x_cost_mat = [[round(val, 4) for val in row]
                                for row in expected_x_cost_mat]
        x_cost_mat = [[round(val, 4) for val in row] for row in x_cost_mat]
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def test_get_extended_cost_matrix_metric_not_found_in_any(self):
        # host3: foo=3072, bar=1
        # host4: foo=8192, bar=0
        # host5: foo=768, bar=0, zot=1
        # host6: foo=2048, bar=0, zot=2
        setting = ['foo=0.0001', 'non_exist_met=2']
        self.flags(weight_setting=setting, group='metrics')

        fake_hosts, fake_filter_properties = self._get_fake_cost_inputs()
        fake_hosts = fake_hosts[2:6]

        fake_cost = self.cost_classes[0]()

        expected_x_cost_mat = [
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0]]

        x_cost_mat = fake_cost.get_extended_cost_matrix(fake_hosts,
                                                    fake_filter_properties)
        expected_x_cost_mat = [[round(val, 4) for val in row]
                                for row in expected_x_cost_mat]
        x_cost_mat = [[round(val, 4) for val in row] for row in x_cost_mat]
        self.assertEqual(expected_x_cost_mat, x_cost_mat)

    def _check_parsing_result(self, cost, setting, results):
        self.flags(weight_setting=setting, group='metrics')
        cost._parse_setting()
        self.assertTrue(len(results) == len(cost.setting))
        for item in results:
            self.assertTrue(item in cost.setting)

    def test_metrics_cost_parse_setting(self):
        fake_cost = self.cost_classes[0]()
        self._check_parsing_result(fake_cost,
                                   ['foo=1'],
                                   [('foo', 1.0)])
        self._check_parsing_result(fake_cost,
                                   ['foo=1', 'bar=-2.1'],
                                   [('foo', 1.0), ('bar', -2.1)])
        self._check_parsing_result(fake_cost,
                                   ['foo=a1', 'bar=-2.1'],
                                   [('bar', -2.1)])
        self._check_parsing_result(fake_cost,
                                   ['foo', 'bar=-2.1'],
                                   [('bar', -2.1)])
        self._check_parsing_result(fake_cost,
                                   ['=5', 'bar=-2.1'],
                                   [('bar', -2.1)])

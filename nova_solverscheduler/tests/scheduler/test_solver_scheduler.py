# Copyright (c) 2014 Cisco Systems Inc.
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
Tests For Solver Scheduler.
"""

import mock

from nova import context
from nova import exception
from nova.tests.unit.scheduler import test_scheduler
from nova_solverscheduler.scheduler import solver_scheduler
from nova_solverscheduler.scheduler import solver_scheduler_host_manager \
        as host_manager
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes


def fake_get_hosts_stripping_ignored_and_forced(hosts, filter_properties):
    return list(hosts)


def fake_get_group_filtered_hosts(hosts, filter_properties, index):
    group_hosts = filter_properties.get('group_hosts') or []
    if group_hosts:
        hosts = list(hosts)
        hosts.pop(0)
        return hosts
    else:
        return list(hosts)


class SolverSchedulerTestCase(test_scheduler.SchedulerTestCase):
    """Test case for Solver Scheduler."""

    driver_cls = solver_scheduler.ConstraintSolverScheduler

    def setUp(self):
        super(SolverSchedulerTestCase, self).setUp()

    @mock.patch.object(host_manager.SolverSchedulerHostManager,
                        '_init_instance_info')
    @mock.patch.object(host_manager.SolverSchedulerHostManager,
                        '_init_aggregates')
    @mock.patch('nova.objects.ServiceList.get_by_binary',
                return_value=fakes.SERVICES)
    @mock.patch('nova.objects.InstanceList.get_by_host')
    @mock.patch('nova.objects.ComputeNodeList.get_all',
                return_value=fakes.COMPUTE_NODES_OBJ)
    @mock.patch('nova.db.instance_extra_get_by_instance_uuid',
                return_value={'numa_topology': None,
                              'pci_requests': None})
    def test_schedule_happy_day(self, mock_get_extra, mock_get_all,
                                mock_by_host, mock_get_by_binary,
                                mock_init_agg, mock_init_inst):
        """Make sure there's nothing glaringly wrong with _schedule()
        by doing a happy day pass through.
        """
        self.flags(scheduler_host_manager='nova_solverscheduler.scheduler.'
                'solver_scheduler_host_manager.SolverSchedulerHostManager')
        self.flags(scheduler_solver_constraints=[], group='solver_scheduler')

        sched = fakes.FakeSolverScheduler()
        fake_context = context.RequestContext('user', 'project',
                is_admin=True)

        self.stubs.Set(sched.host_manager,
                       'get_hosts_stripping_ignored_and_forced',
                fake_get_hosts_stripping_ignored_and_forced)

        request_spec = {'num_instances': 10,
                        'instance_type': {'memory_mb': 512, 'root_gb': 512,
                                          'ephemeral_gb': 0,
                                          'vcpus': 1},
                        'instance_properties': {'project_id': 1,
                                                'root_gb': 512,
                                                'memory_mb': 512,
                                                'ephemeral_gb': 0,
                                                'vcpus': 1,
                                                'os_type': 'Linux'}}

        selected_hosts = sched._schedule(fake_context, request_spec, {})
        self.assertEqual(10, len(selected_hosts))
        for host in selected_hosts:
            self.assertTrue(host is not None)

    @mock.patch.object(host_manager.SolverSchedulerHostManager,
                        '_init_instance_info')
    @mock.patch.object(host_manager.SolverSchedulerHostManager,
                        '_init_aggregates')
    @mock.patch('nova.objects.ServiceList.get_by_binary',
                return_value=fakes.SERVICES)
    @mock.patch('nova.objects.InstanceList.get_by_host')
    @mock.patch('nova.objects.ComputeNodeList.get_all',
                return_value=fakes.COMPUTE_NODES_OBJ)
    @mock.patch('nova.db.instance_extra_get_by_instance_uuid',
                return_value={'numa_topology': None,
                              'pci_requests': None})
    def test_schedule_chooses_best_host(self, mock_get_extra, mock_get_all,
                                        mock_by_host, mock_get_by_binary,
                                        mock_init_agg, mock_init_inst):
        """The host with the highest free_ram_mb will be chosen!
        """
        self.flags(scheduler_host_manager='nova_solverscheduler.scheduler.'
                'solver_scheduler_host_manager.SolverSchedulerHostManager')
        self.flags(scheduler_solver_constraints=[], group='solver_scheduler')
        self.flags(ram_weight_multiplier=1)

        sched = fakes.FakeSolverScheduler()

        highest_free_ram = 0
        for node in fakes.COMPUTE_NODES:
            if (node.get('hypervisor_hostname', None) and
               node.get('free_ram_mb', 0) and
               node.get('service', None) and
               node['service'].get('host', None)):
                host = node['service']['host']
                hypervisor_hostname = node['hypervisor_hostname']
                free_ram_mb = node['free_ram_mb']
                if free_ram_mb > highest_free_ram:
                    highest_free_ram = free_ram_mb
                    best_host = (str(host), str(hypervisor_hostname))

        self.stubs.Set(sched.host_manager,
                       'get_hosts_stripping_ignored_and_forced',
                       fake_get_hosts_stripping_ignored_and_forced)

        instance_properties = {'project_id': 1,
                                'root_gb': 512,
                                'memory_mb': 512,
                                'ephemeral_gb': 0,
                                'vcpus': 1,
                                'os_type': 'Linux'}
        request_spec = dict(instance_properties=instance_properties,
                            instance_type={'memory_mb': 512})
        filter_properties = {}

        hosts = sched._schedule(self.context, request_spec,
                                filter_properties=filter_properties)
        # one host should be chosen
        self.assertEqual(1, len(hosts))
        selected_host = hosts.pop(0)
        self.assertEqual(best_host, (selected_host.obj.host,
                                    selected_host.obj.nodename))

    @mock.patch.object(host_manager.SolverSchedulerHostManager,
                        '_init_instance_info')
    @mock.patch.object(host_manager.SolverSchedulerHostManager,
                        '_init_aggregates')
    @mock.patch('nova.objects.ServiceList.get_by_binary',
                return_value=fakes.SERVICES)
    @mock.patch('nova.objects.InstanceList.get_by_host')
    @mock.patch('nova.objects.ComputeNodeList.get_all',
                return_value=fakes.COMPUTE_NODES_OBJ)
    @mock.patch('nova.db.instance_extra_get_by_instance_uuid',
                return_value={'numa_topology': None,
                              'pci_requests': None})
    def test_select_destinations(self, mock_get_extra, mock_get_all,
                                mock_by_host, mock_get_by_binary,
                                mock_init_agg, mock_init_inst):
        """select_destinations is basically a wrapper around _schedule().

        Similar to the _schedule tests, this just does a happy path test to
        ensure there is nothing glaringly wrong.
        """
        self.flags(scheduler_host_manager='nova_solverscheduler.scheduler.'
                'solver_scheduler_host_manager.SolverSchedulerHostManager')
        self.flags(scheduler_solver_constraints=[], group='solver_scheduler')

        sched = fakes.FakeSolverScheduler()
        fake_context = context.RequestContext('user', 'project',
                                              is_admin=True)

        self.stubs.Set(sched.host_manager,
                       'get_hosts_stripping_ignored_and_forced',
                       fake_get_hosts_stripping_ignored_and_forced)

        request_spec = {'instance_type': {'memory_mb': 512, 'root_gb': 512,
                                          'ephemeral_gb': 0,
                                          'vcpus': 1},
                        'instance_properties': {'project_id': 1,
                                                'root_gb': 512,
                                                'memory_mb': 512,
                                                'ephemeral_gb': 0,
                                                'vcpus': 1,
                                                'os_type': 'Linux'},
                        'num_instances': 1}

        dests = sched.select_destinations(fake_context, request_spec, {})
        (host, node) = (dests[0]['host'], dests[0]['nodename'])
        self.assertTrue(host is not None)
        self.assertTrue(node is not None)

    def test_select_destinations_no_valid_host(self):

        def _return_no_host(*args, **kwargs):
            return []

        self.stubs.Set(self.driver, '_schedule', _return_no_host)
        self.assertRaises(exception.NoValidHost,
                          self.driver.select_destinations, self.context,
                          {'num_instances': 1}, {})

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

import contextlib
import mock

from nova.compute import utils as compute_utils
from nova.compute import vm_states
from nova import context
from nova import db
from nova import exception
from nova.scheduler import driver
from nova.scheduler import host_manager
from nova.scheduler import solver_scheduler
from nova.scheduler import weights
from nova.tests.scheduler import fakes
from nova.tests.scheduler import test_scheduler


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

    def test_run_instance_no_hosts(self):

        def _fake_empty_call_zone_method(*args, **kwargs):
            return []

        sched = fakes.FakeSolverScheduler()

        uuid = 'fake-uuid1'
        fake_context = context.RequestContext('user', 'project')
        instance_properties = {'project_id': 1, 'os_type': 'Linux'}
        request_spec = {'instance_type': {'memory_mb': 1, 'root_gb': 1,
                                          'ephemeral_gb': 0},
                        'instance_properties': instance_properties,
                        'instance_uuids': [uuid]}
        with contextlib.nested(
            mock.patch.object(compute_utils, 'add_instance_fault_from_exc'),
            mock.patch.object(db, 'instance_update_and_get_original'),
            mock.patch.object(db, 'compute_node_get_all')) as (
                add_instance, get_original, get_all):
            get_original.return_value = ({}, {})
            get_all.return_value = []
            sched.schedule_run_instance(
                fake_context, request_spec, None, None, None, None, {}, False)
            add_instance.assert_called_once_with(fake_context, mock.ANY, {},
                                                 mock.ANY, mock.ANY)
            get_original.assert_called_once_with(fake_context, uuid,
                                                 {'vm_state': vm_states.ERROR,
                                                  'task_state': None})
            get_all.assert_called_once_with(mock.ANY)

    def test_run_instance_non_admin(self):
        self.was_admin = False

        def fake_get(context, *args, **kwargs):
            # make sure this is called with admin context, even though
            # we're using user context below
            self.was_admin = context.is_admin
            return {}

        sched = fakes.FakeSolverScheduler()
        self.stubs.Set(sched.host_manager, 'get_all_host_states', fake_get)

        fake_context = context.RequestContext('user', 'project')

        uuid = 'fake-uuid1'
        instance_properties = {'project_id': 1, 'os_type': 'Linux'}
        request_spec = {'instance_type': {'memory_mb': 1, 'local_gb': 1},
                        'instance_properties': instance_properties,
                        'instance_uuids': [uuid]}
        with contextlib.nested(
            mock.patch.object(compute_utils, 'add_instance_fault_from_exc'),
            mock.patch.object(db, 'instance_update_and_get_original')) as (
                add_instance, get_original):
            get_original.return_value = ({}, {})
            sched.schedule_run_instance(
                fake_context, request_spec, None, None, None, None, {}, False)
            add_instance.assert_called_once_with(fake_context, mock.ANY, {},
                                                 mock.ANY, mock.ANY)
            get_original.assert_called_once_with(fake_context, uuid,
                                                 {'vm_state': vm_states.ERROR,
                                                  'task_state': None})
            self.assertTrue(self.was_admin)

    def test_scheduler_includes_launch_index(self):
        fake_context = context.RequestContext('user', 'project')
        instance_opts = {'fake_opt1': 'meow'}
        request_spec = {'instance_uuids': ['fake-uuid1', 'fake-uuid2'],
                        'instance_properties': instance_opts}

        instance1 = {'uuid': 'fake-uuid1'}
        instance2 = {'uuid': 'fake-uuid2'}

        actual_launch_indices = []
        # Retrieving the launch_index value from the request_spec (the 3rd
        # argument of the _provision_resource method) using the side_effect

        def provision_side_effect(*args, **kwargs):
            if 'instance_properties' in args[2]:
                if 'launch_index' in args[2]['instance_properties']:
                    actual_launch_indices.append(
                        args[2]['instance_properties']['launch_index'])
            if len(actual_launch_indices) == 1:
                # Setting the return_value for the first call
                return instance1
            else:
                # Setting the return_value for the second call
                return instance2

        with contextlib.nested(
            mock.patch.object(self.driver, '_schedule'),
            mock.patch.object(self.driver, '_provision_resource')) as (
                schedule_mock, provision_mock):
            schedule_mock.return_value = ['host1', 'host2']
            provision_mock.side_effect = provision_side_effect
            self.driver.schedule_run_instance(fake_context, request_spec,
                    None, None, None, None, {}, False)
            schedule_mock.assert_called_once_with(fake_context, request_spec,
                    {}, ['fake-uuid1', 'fake-uuid2'])
            call_args_list_expected = [(fake_context, 'host1', request_spec,
                {}, None, None, None, None, {'instance_uuid': 'fake-uuid1',
                'legacy_bdm_in_spec': False}),
                (fake_context, 'host2', request_spec, {}, None, None, None,
                 None, {'instance_uuid': 'fake-uuid2',
                 'legacy_bdm_in_spec': False})]
            self.assertEqual(2, provision_mock.call_count)
            for i in range(provision_mock.call_count):
                self.assertEqual(list(call_args_list_expected[i]),
                                 list(provision_mock.call_args_list[i][0]) +
                                 [provision_mock.call_args_list[i][1]])
            expected_launch_indices = [0, 1]
            self.assertEqual(expected_launch_indices, actual_launch_indices)

    def test_schedule_happy_day(self):
        """Make sure there's nothing glaringly wrong with _schedule()
        by doing a happy day pass through.
        """

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

        with mock.patch.object(db, 'compute_node_get_all') as get_all:
            get_all.return_value = fakes.COMPUTE_NODES
            selected_hosts = sched._schedule(fake_context, request_spec, {})
            get_all.assert_called_once_with(mock.ANY)
            self.assertEqual(10, len(selected_hosts))
            for host in selected_hosts:
                self.assertTrue(host is not None)

    def test_max_attempts(self):
        self.flags(scheduler_max_attempts=4)

        sched = fakes.FakeSolverScheduler()
        self.assertEqual(4, sched._max_attempts())

    def test_invalid_max_attempts(self):
        self.flags(scheduler_max_attempts=0)

        sched = fakes.FakeSolverScheduler()
        self.assertRaises(exception.NovaException, sched._max_attempts)

    def test_retry_disabled(self):
        # Retry info should not get populated when re-scheduling is off.
        self.flags(scheduler_max_attempts=1)
        sched = fakes.FakeSolverScheduler()

        instance_properties = {'project_id': '12345', 'os_type': 'Linux'}
        request_spec = dict(instance_properties=instance_properties)
        filter_properties = {}

        with mock.patch.object(db, 'compute_node_get_all') as get_all:
            get_all.return_value = []
            sched._schedule(self.context, request_spec,
                            filter_properties=filter_properties)
            get_all.assert_called_once_with(mock.ANY)
            # should not have retry info in the populated filter properties:
            self.assertFalse("retry" in filter_properties)

    def test_retry_attempt_one(self):
        # Test retry logic on initial scheduling attempt.
        self.flags(scheduler_max_attempts=2)
        sched = fakes.FakeSolverScheduler()

        instance_properties = {'project_id': '12345', 'os_type': 'Linux'}
        request_spec = dict(instance_properties=instance_properties)
        filter_properties = {}

        with mock.patch.object(db, 'compute_node_get_all') as get_all:
            get_all.return_value = []
            sched._schedule(self.context, request_spec,
                            filter_properties=filter_properties)
            get_all.assert_called_once_with(mock.ANY)
            num_attempts = filter_properties['retry']['num_attempts']
            self.assertEqual(1, num_attempts)

    def test_retry_attempt_two(self):
        # Test retry logic when re-scheduling.
        self.flags(scheduler_max_attempts=2)
        sched = fakes.FakeSolverScheduler()

        instance_properties = {'project_id': '12345', 'os_type': 'Linux'}
        request_spec = dict(instance_properties=instance_properties)

        retry = dict(num_attempts=1)
        filter_properties = dict(retry=retry)

        with mock.patch.object(db, 'compute_node_get_all') as get_all:
            get_all.return_value = []
            sched._schedule(self.context, request_spec,
                            filter_properties=filter_properties)
            get_all.assert_called_once_with(mock.ANY)
            num_attempts = filter_properties['retry']['num_attempts']
            self.assertEqual(2, num_attempts)

    def test_retry_exceeded_max_attempts(self):
        # Test for necessary explosion when max retries is exceeded and that
        # the information needed in request_spec is still present for error
        # handling
        self.flags(scheduler_max_attempts=2)
        sched = fakes.FakeSolverScheduler()

        instance_properties = {'project_id': '12345', 'os_type': 'Linux'}
        instance_uuids = ['fake-id']
        request_spec = dict(instance_properties=instance_properties,
                            instance_uuids=instance_uuids)

        retry = dict(num_attempts=2)
        filter_properties = dict(retry=retry)

        self.assertRaises(exception.NoValidHost, sched.schedule_run_instance,
                          self.context, request_spec, admin_password=None,
                          injected_files=None, requested_networks=None,
                          is_first_time=False,
                          filter_properties=filter_properties,
                          legacy_bdm_in_spec=False)
        uuids = request_spec.get('instance_uuids')
        self.assertEqual(instance_uuids, uuids)

    def test_schedule_chooses_best_host(self):
        """The host with the highest free_ram_mb will be chosen!
        """

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
        request_spec = dict(instance_properties=instance_properties)
        filter_properties = {}

        with mock.patch.object(db, 'compute_node_get_all') as get_all:
            get_all.return_value = fakes.COMPUTE_NODES
            hosts = sched._schedule(self.context, request_spec,
                                    filter_properties=filter_properties)
            get_all.assert_called_once_with(mock.ANY)
            # one host should be chosen
            self.assertEqual(1, len(hosts))
            selected_host = hosts.pop(0)
            self.assertEqual(best_host, (selected_host.obj.host,
                                         selected_host.obj.nodename))

    def test_select_destinations(self):
        """select_destinations is basically a wrapper around _schedule().

        Similar to the _schedule tests, this just does a happy path test to
        ensure there is nothing glaringly wrong.
        """

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

        with mock.patch.object(db, 'compute_node_get_all') as get_all:
            get_all.return_value = fakes.COMPUTE_NODES
            dests = sched.select_destinations(fake_context, request_spec,
                                              {})
            get_all.assert_called_once_with(mock.ANY)
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

    def test_handles_deleted_instance(self):
        """Test instance deletion while being scheduled."""

        def _raise_instance_not_found(*args, **kwargs):
            raise exception.InstanceNotFound(instance_id='123')

        self.stubs.Set(driver, 'instance_update_db',
                       _raise_instance_not_found)

        sched = fakes.FakeSolverScheduler()

        fake_context = context.RequestContext('user', 'project')
        host = host_manager.HostState('host2', 'node2')
        selected_host = weights.WeighedHost(host, 1)
        filter_properties = {}

        uuid = 'fake-uuid1'
        instance_properties = {'project_id': 1, 'os_type': 'Linux'}
        request_spec = {'instance_type': {'memory_mb': 1, 'local_gb': 1},
                        'instance_properties': instance_properties,
                        'instance_uuids': [uuid]}
        sched._provision_resource(fake_context, selected_host,
                                  request_spec, filter_properties,
                                  None, None, None, None)

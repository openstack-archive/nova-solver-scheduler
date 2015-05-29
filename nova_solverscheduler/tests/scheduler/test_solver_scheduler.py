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
import mox
import uuid

from nova.compute import utils as compute_utils
from nova.compute import vm_states
from nova import context
from nova import db
from nova import exception
from nova import objects
from nova.scheduler import driver
from nova.scheduler import host_manager
from nova.scheduler import weights
from nova.tests import fake_instance
from nova.tests.scheduler import test_scheduler
from nova_solverscheduler.scheduler import solver_scheduler
from nova_solverscheduler import solver_scheduler_exception
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

        self.mox.StubOutWithMock(compute_utils, 'add_instance_fault_from_exc')
        self.mox.StubOutWithMock(db, 'instance_update_and_get_original')
        old_ref, new_ref = db.instance_update_and_get_original(fake_context,
                uuid, {'vm_state': vm_states.ERROR, 'task_state':
                    None}).AndReturn(({}, {}))
        compute_utils.add_instance_fault_from_exc(fake_context, new_ref,
                mox.IsA(exception.NoValidHost), mox.IgnoreArg())

        self.mox.StubOutWithMock(db, 'compute_node_get_all')
        db.compute_node_get_all(mox.IgnoreArg()).AndReturn([])

        self.mox.ReplayAll()
        sched.schedule_run_instance(
                fake_context, request_spec, None, None,
                None, None, {}, False)

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
        self.mox.StubOutWithMock(compute_utils, 'add_instance_fault_from_exc')
        self.mox.StubOutWithMock(db, 'instance_update_and_get_original')
        old_ref, new_ref = db.instance_update_and_get_original(fake_context,
                uuid, {'vm_state': vm_states.ERROR, 'task_state':
                    None}).AndReturn(({}, {}))
        compute_utils.add_instance_fault_from_exc(fake_context, new_ref,
                mox.IsA(exception.NoValidHost), mox.IgnoreArg())
        self.mox.ReplayAll()
        sched.schedule_run_instance(
                fake_context, request_spec, None, None, None, None, {}, False)
        self.assertTrue(self.was_admin)

    def test_schedule_happy_day(self):
        """Make sure there's nothing glaringly wrong with _schedule()
        by doing a happy day pass through.
        """
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

        with mock.patch.object(db, 'compute_node_get_all') as get_all:
            get_all.return_value = fakes.COMPUTE_NODES
            selected_hosts = sched._schedule(fake_context, request_spec, {})
            get_all.assert_called_once_with(mock.ANY)
            self.assertEqual(10, len(selected_hosts))
            for host in selected_hosts:
                self.assertTrue(host is not None)

    def _create_server_group(self, policy='anti-affinity'):
        instance = fake_instance.fake_instance_obj(self.context,
                params={'host': 'hostA'})

        group = objects.InstanceGroup()
        group.name = 'pele'
        group.uuid = str(uuid.uuid4())
        group.members = [instance.uuid]
        group.policies = [policy]
        return group

    def _group_details_in_filter_properties(self, group, func='get_by_uuid',
                                            hint=None, policy=None):
        sched = fakes.FakeSolverScheduler()

        filter_properties = {
            'scheduler_hints': {
                'group': hint,
            },
            'group_hosts': ['hostB'],
        }

        with contextlib.nested(
            mock.patch.object(objects.InstanceGroup, func,
                                return_value=group),
            mock.patch.object(objects.InstanceGroup, 'get_hosts',
                                return_value=['hostA']),
        ) as (get_group, get_hosts):
            sched._supports_anti_affinity = True
            update_group_hosts = sched._setup_instance_group(self.context,
                    filter_properties)
            self.assertTrue(update_group_hosts)
            self.assertEqual(set(['hostA', 'hostB']),
                             filter_properties['group_hosts'])
            self.assertEqual([policy], filter_properties['group_policies'])

    def test_group_details_in_filter_properties(self):
        self.flags(scheduler_solver_constraints=[
                'ServerGroupAffinityConstraint',
                'ServerGroupAntiAffinityConstraint'],
                group='solver_scheduler')
        for policy in ['affinity', 'anti-affinity']:
            group = self._create_server_group(policy)
            self._group_details_in_filter_properties(group, func='get_by_uuid',
                                                     hint=group.uuid,
                                                     policy=policy)

    def _group_constraint_with_constraint_not_configured(self, policy):
        wrong_constraint = {
            'affinity': 'ServerGroupAntiAffinityConstraint',
            'anti-affinity': 'ServerGroupAffinityConstraint',
        }
        self.flags(scheduler_solver_constraints=[wrong_constraint[policy]],
                    group='solver_scheduler')
        sched = fakes.FakeSolverScheduler()

        instance = fake_instance.fake_instance_obj(self.context,
                params={'host': 'hostA'})

        group = objects.InstanceGroup()
        group.uuid = str(uuid.uuid4())
        group.members = [instance.uuid]
        group.policies = [policy]

        filter_properties = {
            'scheduler_hints': {
                'group': group.uuid,
            },
        }

        with contextlib.nested(
            mock.patch.object(objects.InstanceGroup, 'get_by_uuid',
                              return_value=group),
            mock.patch.object(objects.InstanceGroup, 'get_hosts',
                              return_value=['hostA']),
        ) as (get_group, get_hosts):
            self.assertRaises(exception.NoValidHost,
                              sched._setup_instance_group, self.context,
                              filter_properties)

    def test_group_constraint_with_constraint_not_configured(self):
        policies = ['anti-affinity', 'affinity']
        for policy in policies:
            self._group_constraint_with_constraint_not_configured(policy)

    def test_group_uuid_details_in_filter_properties(self):
        group = self._create_server_group()
        self._group_details_in_filter_properties(group, 'get_by_uuid',
                                                 group.uuid, 'anti-affinity')

    def test_group_name_details_in_filter_properties(self):
        group = self._create_server_group()
        self._group_details_in_filter_properties(group, 'get_by_name',
                                                 group.name, 'anti-affinity')

    def test_schedule_chooses_best_host(self):
        """The host with the highest free_ram_mb will be chosen!
        """
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

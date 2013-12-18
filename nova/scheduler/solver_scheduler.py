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
A Solver scheduler that can be used to solve the nova compute scheduling
problem with complex constraints, and can be used to optimize on certain
cost metrics. The solution is designed to work with pluggable solvers.
A default solver implementation that uses PULP is included.
"""

from oslo.config import cfg

from nova.compute import flavors
from nova.compute import rpcapi as compute_rpcapi
from nova import db
from nova import exception
from nova.openstack.common.gettextutils import _
from nova.openstack.common import importutils
from nova.openstack.common import log as logging
from nova.openstack.common.notifier import api as notifier
from nova.scheduler import driver
from nova.scheduler import scheduler_options
from nova.scheduler import utils as scheduler_utils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

solver_opts = [
    cfg.StrOpt('scheduler_host_solver',
        default='nova.scheduler.solvers.hosts_pulp_solver.HostsPulpSolver',
        help='The scheduler host solver to use'),
    ]

CONF.register_opts(solver_opts)


class ConstraintSolverScheduler(driver.Scheduler):
    """Scheduler that picks hosts using a Constraint Solver
       based problem solving for constraint satisfaction
       and optimization.
    """
    def __init__(self, *args, **kwargs):
        super(ConstraintSolverScheduler, self).__init__(*args, **kwargs)
        self.options = scheduler_options.SchedulerOptions()
        self.compute_rpcapi = compute_rpcapi.ComputeAPI()
        #The hosts solver to use
        self.hosts_solver = importutils.import_object(
                CONF.scheduler_host_solver)

    def schedule_run_instance(self, context, request_spec,
                              admin_password, injected_files,
                              requested_networks, is_first_time,
                              filter_properties, legacy_bdm_in_spec):
        """This method is called from nova.compute.api to provision
        an instance.  We first create a Host - Instance assignment plan
        and then provision.

        Returns a list of the instances created.
        """
        payload = dict(request_spec=request_spec)
        notifier.notify(context, notifier.publisher_id("scheduler"),
                        'scheduler.run_instance.start', notifier.INFO, payload)

        instance_uuids = request_spec.get('instance_uuids')
        LOG.info(_("Attempting to build %(num_instances)d instance(s) "
                    "uuids: %(instance_uuids)s"),
                  {'num_instances': len(instance_uuids),
                   'instance_uuids': instance_uuids})
        LOG.debug(_("Request Spec: %s") % request_spec)

        selected_hosts = self._schedule(context, request_spec,
                                       filter_properties, instance_uuids)

        # NOTE: Pop instance_uuids as individual creates do not need the
        # set of uuids. Do not pop before here as the upper exception
        # handler fo NoValidHost needs the uuid to set error state
        instance_uuids = request_spec.pop('instance_uuids')

        # NOTE(comstud): Make sure we do not pass this through.  It
        # contains an instance of RpcContext that cannot be serialized.
        filter_properties.pop('context', None)

        for num, instance_uuid in enumerate(instance_uuids):
            request_spec['instance_properties']['launch_index'] = num

            try:
                try:
                    selected_host = selected_hosts.pop(0)
                    LOG.info(_("Choosing host %(selected_host)s "
                                "for instance %(instance_uuid)s"),
                              {'selected_host': selected_host,
                               'instance_uuid': instance_uuid})
                except IndexError:
                    raise exception.NoValidHost(reason="")

                self._provision_resource(context, selected_host,
                                         request_spec,
                                         filter_properties,
                                         requested_networks,
                                         injected_files, admin_password,
                                         is_first_time,
                                         instance_uuid=instance_uuid)
            except Exception as ex:
                # NOTE(vish): we don't reraise the exception here to make sure
                #             that all instances in the request get set to
                #             error properly
                driver.handle_schedule_error(context, ex, instance_uuid,
                                             request_spec)
            # scrub retry host list in case we're scheduling multiple
            # instances:
            retry = filter_properties.get('retry', {})
            retry['hosts'] = []

        notifier.notify(context, notifier.publisher_id("scheduler"),
                        'scheduler.run_instance.end', notifier.INFO, payload)

    def select_hosts(self, context, request_spec, filter_properties):
        """Selects a filtered set of hosts."""
        instance_uuids = request_spec.get('instance_uuids')
        hosts = [host.host for host in self._schedule(context,
            request_spec, filter_properties, instance_uuids)]
        if not hosts:
            raise exception.NoValidHost(reason="")
        return hosts

    def select_destinations(self, context, request_spec, filter_properties):
        """Selects a filtered set of hosts and nodes."""
        num_instances = request_spec['num_instances']
        instance_uuids = request_spec.get('instance_uuids')
        selected_hosts = self._schedule(context, request_spec,
                                        filter_properties, instance_uuids)

        # Couldn't fulfill the request_spec
        if len(selected_hosts) < num_instances:
            raise exception.NoValidHost(reason='')

        dests = [dict(host=host.host, nodename=host.nodename,
                      limits=host.limits) for host in selected_hosts]
        return dests

    def _schedule(self, context, request_spec, filter_properties,
                  instance_uuids=None):
        """Returns a list of hosts that meet the required specs for
        each instance in the list of instance_uuids.
         Here each instance in instance_uuids have the same requirement
         as specified by request_spec.
        """
        elevated = context.elevated()
        instance_properties = request_spec['instance_properties']
        instance_type = request_spec.get("instance_type", None)
        # Get the group
        update_group_hosts = False
        scheduler_hints = filter_properties.get('scheduler_hints') or {}
        group = scheduler_hints.get('group', None)
        if group:
            group_hosts = self.group_hosts(elevated, group)
            update_group_hosts = True
            if 'group_hosts' not in filter_properties:
                filter_properties.update({'group_hosts': []})
            configured_hosts = filter_properties['group_hosts']
            filter_properties['group_hosts'] = configured_hosts + group_hosts

        config_options = self._get_configuration_options()

        # check retry policy.  Rather ugly use of instance_uuids[0]...
        # but if we've exceeded max retries... then we really only
        # have a single instance.
        properties = instance_properties.copy()
        if instance_uuids:
            properties['uuid'] = instance_uuids[0]
        self._populate_retry(filter_properties, properties)

        filter_properties.update({'context': context,
                                  'request_spec': request_spec,
                                  'config_options': config_options,
                                  'instance_type': instance_type})

        self.populate_filter_properties(request_spec,
                                        filter_properties)

        # this returns a host iterator
        hosts = self.host_manager.get_all_host_states(elevated)

        selected_hosts = []

        hosts = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                      hosts, filter_properties)

        force_hosts = filter_properties.get('force_hosts', [])
        force_nodes = filter_properties.get('force_nodes', [])

        if force_hosts or force_nodes:
        #NOTE(Yathi): Skipping the solver when forcing host or node
            selected_hosts = list(hosts)
        else:
            #NOTE(Yathi):  Calling the constraint solver here
            #---------------
            list_hosts = list(hosts)
            host_instance_tuples_list = self.hosts_solver.host_solve(
                                             list_hosts, instance_uuids,
                                             request_spec, filter_properties)
            selected_hosts = [host for (host, instance) in
                              host_instance_tuples_list]
            #----------------

        for chosen_host in selected_hosts:
        # Update the host state after deducting the
        # resource used by the instance
            chosen_host.consume_from_instance(instance_properties)
            if update_group_hosts is True:
                filter_properties['group_hosts'].append(chosen_host.host)

        return selected_hosts

    def _provision_resource(self, context, selected_host, request_spec,
            filter_properties, requested_networks, injected_files,
            admin_password, is_first_time, instance_uuid=None):
        """Create the requested resource in this Zone."""
        # NOTE(vish): add our current instance back into the request spec
        request_spec['instance_uuids'] = [instance_uuid]
        #NOTE(Yathi): Not using weights in solver scheduler,
        #but leaving in the payload
        payload = dict(request_spec=request_spec,
                       weighted_host=dict(host=selected_host.host, weight=1),
                       instance_id=instance_uuid)
        notifier.notify(context, notifier.publisher_id("scheduler"),
                        'scheduler.run_instance.scheduled', notifier.INFO,
                        payload)

        # Update the metadata if necessary
        scheduler_hints = filter_properties.get('scheduler_hints') or {}
        group = scheduler_hints.get('group', None)
        values = None
        if group:
            values = request_spec['instance_properties']['system_metadata']
            values.update({'group': group})
            values = {'system_metadata': values}

        try:
            updated_instance = driver.instance_update_db(context,
                    instance_uuid, extra_values=values)

        except exception.InstanceNotFound:
            LOG.warning(_("Instance disappeared during scheduling"),
                        context=context, instance_uuid=instance_uuid)

        else:
            scheduler_utils.populate_filter_properties(filter_properties,
                    selected_host)

            self.compute_rpcapi.run_instance(context,
                    instance=updated_instance,
                    host=selected_host.host,
                    request_spec=request_spec,
                    filter_properties=filter_properties,
                    requested_networks=requested_networks,
                    injected_files=injected_files,
                    admin_password=admin_password,
                    is_first_time=is_first_time,
                    node=selected_host.nodename)

    def _get_configuration_options(self):
        """Fetch options dictionary. Broken out for testing."""
        return self.options.get_configuration()

    def populate_filter_properties(self, request_spec, filter_properties):
        """Stuff things into filter_properties.  Can be overridden in a
        subclass to add more data.
        """
        # Save useful information from the request spec for filter processing:
        project_id = request_spec['instance_properties']['project_id']
        os_type = request_spec['instance_properties']['os_type']
        filter_properties['project_id'] = project_id
        filter_properties['os_type'] = os_type

    def _max_attempts(self):
        max_attempts = CONF.scheduler_max_attempts
        if max_attempts < 1:
            raise exception.NovaException(_("Invalid value for "
                "'scheduler_max_attempts', must be >= 1"))
        return max_attempts

    def _log_compute_error(self, instance_uuid, retry):
        """If the request contained an exception from a previous compute
        build/resize operation, log it to aid debugging
        """
        exc = retry.pop('exc', None)  # string-ified exception from compute
        if not exc:
            return  # no exception info from a prevous attempt, skip

        hosts = retry.get('hosts', None)
        if not hosts:
            return  # no previously attempted hosts, skip

        last_host, last_node = hosts[-1]
        LOG.error(_('Error from last host: %(last_host)s (node %(last_node)s):'
                    ' %(exc)s'),
                  {'last_host': last_host,
                   'last_node': last_node,
                   'exc': exc},
                  instance_uuid=instance_uuid)

    def _populate_retry(self, filter_properties, instance_properties):
        """Populate filter properties with history of retries for this
        request. If maximum retries is exceeded, raise NoValidHost.
        """
        max_attempts = self._max_attempts()
        retry = filter_properties.pop('retry', {})

        if max_attempts == 1:
            # re-scheduling is disabled.
            return

        # retry is enabled, update attempt count:
        if retry:
            retry['num_attempts'] += 1
        else:
            retry = {
                'num_attempts': 1,
                'hosts': []  # list of compute hosts tried
            }
        filter_properties['retry'] = retry

        instance_uuid = instance_properties.get('uuid')
        self._log_compute_error(instance_uuid, retry)

        if retry['num_attempts'] > max_attempts:
            msg = (_('Exceeded max scheduling attempts %(max_attempts)d for '
                     'instance %(instance_uuid)s')
                   % {'max_attempts': max_attempts,
                      'instance_uuid': instance_uuid})
            raise exception.NoValidHost(reason=msg)

    def _get_compute_info(self, context, dest):
        """Get compute node's information
        :param context: security context
        :param dest: hostname (must be compute node)
        :return: dict of compute node information
        """
        service_ref = db.service_get_by_compute_host(context, dest)
        return service_ref['compute_node'][0]

    def _assert_compute_node_has_enough_memory(self, context,
                                              instance_ref, dest):
        """Checks if destination host has enough memory for live migration.


        :param context: security context
        :param instance_ref: nova.db.sqlalchemy.models.Instance object
        :param dest: destination host

        """
        compute = self._get_compute_info(context, dest)
        node = compute.get('hypervisor_hostname')
        host_state = self.host_manager.host_state_cls(dest, node)
        host_state.update_from_compute_node(compute)

        instance_type = flavors.extract_flavor(instance_ref)
        filter_properties = {'instance_type': instance_type}

        hosts = self.host_manager.get_filtered_hosts([host_state],
                                                     filter_properties,
                                                     'RamFilter')
        if not hosts:
            instance_uuid = instance_ref['uuid']
            reason = (_("Unable to migrate %(instance_uuid)s to %(dest)s: "
                        "Lack of memory")
                      % {'instance_uuid': instance_uuid,
                         'dest': dest})
            raise exception.MigrationPreCheckError(reason=reason)

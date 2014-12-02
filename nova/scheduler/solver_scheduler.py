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
A Solver scheduler that can be used to solve the nova compute scheduling
problem with complex constraints, and can be used to optimize on certain
cost metrics. The solution is designed to work with pluggable solvers.
A default solver implementation that uses PULP is included.
"""

from oslo.config import cfg

from nova import exception
from nova.openstack.common.gettextutils import _
from nova.openstack.common import importutils
from nova.openstack.common import log as logging
from nova.scheduler import driver
from nova.scheduler import filter_scheduler
from nova.scheduler import weights

solver_opts = [
    cfg.StrOpt('scheduler_host_solver',
        default='nova.scheduler.solvers.hosts_pulp_solver.HostsPulpSolver',
        help='The pluggable solver implementation to use. By default, a '
              'reference solver implementation is included that models '
              'the problem as a Linear Programming (LP) problem using PULP.'),
    ]

CONF = cfg.CONF
CONF.register_opts(solver_opts, group='solver_scheduler')

LOG = logging.getLogger(__name__)

class ConstraintSolverScheduler(filter_scheduler.FilterScheduler):
    """Scheduler that picks hosts using a Constraint Solver
       based problem solving for constraint satisfaction
       and optimization.
    """
    def __init__(self, *args, **kwargs):
        super(ConstraintSolverScheduler, self).__init__(*args, **kwargs)
        self.hosts_solver = importutils.import_object(
                CONF.solver_scheduler.scheduler_host_solver)

    def schedule_run_instance(self, context, request_spec,
                              admin_password, injected_files,
                              requested_networks, is_first_time,
                              filter_properties, legacy_bdm_in_spec):
        """This method is called from nova.compute.api to provision
        an instance.  We first create a build plan (a list of WeightedHosts)
        and then provision.

        Returns a list of the instances created.
        """
        payload = dict(request_spec=request_spec)
        self.notifier.info(context, 'scheduler.run_instance.start', payload)

        instance_uuids = request_spec.get('instance_uuids')
        LOG.info(_("Attempting to build %(num_instances)d instance(s) "
                    "uuids: %(instance_uuids)s"),
                  {'num_instances': len(instance_uuids),
                   'instance_uuids': instance_uuids})
        LOG.debug(_("Request Spec: %s") % request_spec)

        # Stuff network requests into filter_properties
        # NOTE (Xinyuan): currently for POC only.
        filter_properties['requested_networks'] = requested_networks

        weighed_hosts = self._schedule(context, request_spec,
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
                    weighed_host = weighed_hosts.pop(0)
                    LOG.info(_("Choosing host %(weighed_host)s "
                                "for instance %(instance_uuid)s"),
                              {'weighed_host': weighed_host,
                               'instance_uuid': instance_uuid})
                except IndexError:
                    raise exception.NoValidHost(reason="")

                self._provision_resource(context, weighed_host,
                                         request_spec,
                                         filter_properties,
                                         requested_networks,
                                         injected_files, admin_password,
                                         is_first_time,
                                         instance_uuid=instance_uuid,
                                         legacy_bdm_in_spec=legacy_bdm_in_spec)
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

        self.notifier.info(context, 'scheduler.run_instance.end', payload)

    def _schedule(self, context, request_spec, filter_properties,
                  instance_uuids=None):
        """Returns a list of hosts that meet the required specs,
        ordered by their fitness.
        """
        elevated = context.elevated()
        instance_properties = request_spec['instance_properties']
        instance_type = request_spec.get("instance_type", None)

        update_group_hosts = self._setup_instance_group(context,
                filter_properties)

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

        # Note: Moving the host selection logic to a new method so that
        # the subclasses can override the behavior.
        return self._get_final_host_list(elevated, request_spec,
                                         filter_properties,
                                         instance_properties,
                                         update_group_hosts,
                                         instance_uuids)

    def _get_final_host_list(self, context, request_spec, filter_properties,
                  instance_properties, update_group_hosts=False,
                  instance_uuids=None):
        """Returns the final list of hosts that meet the required specs for
        each instance in the list of instance_uuids.
         Here each instance in instance_uuids have the same requirement
         as specified by request_spec.
        """
        # this returns a host iterator
        hosts = self._get_all_host_states(context)
        selected_hosts = []
        hosts = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                      hosts, filter_properties)
        force_hosts = filter_properties.get('force_hosts', [])
        force_nodes = filter_properties.get('force_nodes', [])
        if force_hosts or force_nodes:
            # NOTE(Yathi): Skipping the solver when forcing host or node
            selected_hosts = list(hosts)
        else:
            list_hosts = list(hosts)
            host_instance_tuples_list = self.hosts_solver.host_solve(
                                             list_hosts, instance_uuids,
                                             request_spec, filter_properties)
            LOG.debug(_("solver results: %(host_instance_list)s") %
                        {"host_instance_list": host_instance_tuples_list})
            # NOTE(Yathi): Not using weights in solver scheduler,
            # but creating a list of WeighedHosts with a default weight of 1
            # to match the common method signatures of the
            # FilterScheduler class
            selected_hosts = [weights.WeighedHost(host, 1)
                              for (host, instance) in
                              host_instance_tuples_list]
        for chosen_host in selected_hosts:
            # Update the host state after deducting the
            # resource used by the instance
            chosen_host.obj.consume_from_instance(instance_properties)
            if update_group_hosts is True:
                filter_properties['group_hosts'].append(chosen_host.obj.host)
        return selected_hosts

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

from nova.openstack.common import importutils
from nova.scheduler import filter_scheduler
from nova.scheduler import weights

CONF = cfg.CONF

solver_opts = [
    cfg.StrOpt('scheduler_host_solver',
        default='nova.scheduler.solvers.hosts_pulp_solver.HostsPulpSolver',
        help='The pluggable solver implementation to use. By default, a '
              'reference solver implementation is included that models '
              'the problem as a Linear Programming (LP) problem using PULP.'),
    ]

CONF.register_opts(solver_opts, group='solver_scheduler')


class ConstraintSolverScheduler(filter_scheduler.FilterScheduler):
    """Scheduler that picks hosts using a Constraint Solver
       based problem solving for constraint satisfaction
       and optimization.
    """
    def __init__(self, *args, **kwargs):
        super(ConstraintSolverScheduler, self).__init__(*args, **kwargs)
        self.hosts_solver = importutils.import_object(
                CONF.solver_scheduler.scheduler_host_solver)

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

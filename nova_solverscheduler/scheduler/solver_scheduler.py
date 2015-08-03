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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils

from nova.scheduler import filter_scheduler
from nova.scheduler import weights

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

solver_opts = [
    cfg.StrOpt('scheduler_host_solver',
                default='nova_solverscheduler.scheduler.solvers.fast_solver.'
                        'FastSolver',
                help='The pluggable solver implementation to use. By '
                     'default, use the FastSolver.'),
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

    def _schedule(self, context, request_spec, filter_properties):
        """Returns a list of hosts that meet the required specs,
        ordered by their fitness.
        """
        instance_type = request_spec.get("instance_type", None)
        instance_uuids = request_spec.get("instance_uuids", None)

        config_options = self._get_configuration_options()

        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)

        # initilize an empty key-value cache to be used in solver for internal
        # temporary data storage
        solver_cache = {}

        filter_properties.update({'context': context,
                                  'request_spec': request_spec,
                                  'config_options': config_options,
                                  'instance_type': instance_type,
                                  'num_instances': num_instances,
                                  'instance_uuids': instance_uuids,
                                  'solver_cache': solver_cache})

        self.populate_filter_properties(request_spec, filter_properties)

        # NOTE(Yathi): Moving the host selection logic to a new method so that
        # the subclasses can override the behavior.
        selected_hosts = self._get_selected_hosts(context, filter_properties)

        # clear solver's memory after scheduling process
        filter_properties.pop('solver_cache')

        return selected_hosts

    def _get_selected_hosts(self, context, filter_properties):
        """Returns the list of hosts that meet the required specs for
        each instance in the list of instance_uuids.
         Here each instance in instance_uuids have the same requirement
         as specified by request_spec.
        """
        elevated = context.elevated()
        # this returns a host iterator
        hosts = self._get_all_host_states(elevated)
        selected_hosts = []
        hosts = self.host_manager.get_hosts_stripping_ignored_and_forced(
                                      hosts, filter_properties)

        list_hosts = list(hosts)
        LOG.debug("host state list: %(hoststates)s",
                  {"hoststates": list_hosts})
        LOG.debug("filter properties given to solver: %(prop)s",
                  {"prop": filter_properties})
        host_instance_combinations = self.hosts_solver.solve(
                                            list_hosts, filter_properties)
        LOG.debug("solver results: %(host_instance_tuples_list)s",
                    {"host_instance_tuples_list": host_instance_combinations})
        # NOTE(Yathi): Not using weights in solver scheduler,
        # but creating a list of WeighedHosts with a default weight of 1
        # to match the common method signatures of the
        # FilterScheduler class
        selected_hosts = [weights.WeighedHost(host, 1)
                            for (host, instance) in host_instance_combinations]

        return selected_hosts

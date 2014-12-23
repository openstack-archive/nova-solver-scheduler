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
from nova.openstack.common.gettextutils import _
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
        hosts = self._get_hosts_stripping_ignored_and_forced(
                                      hosts, filter_properties)
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

    def _get_hosts_stripping_ignored_and_forced(self, hosts,
            filter_properties):
        """Filter hosts by stripping any ignored hosts and
           matching any forced hosts or nodes.
        """

        def _strip_ignore_hosts(host_map, hosts_to_ignore):
            ignored_hosts = []
            for host in hosts_to_ignore:
                for (hostname, nodename) in host_map.keys():
                    if host == hostname:
                        del host_map[(hostname, nodename)]
                        ignored_hosts.append(host)
            ignored_hosts_str = ', '.join(ignored_hosts)
            msg = _('Host filter ignoring hosts: %s')
            LOG.audit(msg % ignored_hosts_str)

        def _match_forced_hosts(host_map, hosts_to_force):
            forced_hosts = []
            for (hostname, nodename) in host_map.keys():
                if hostname not in hosts_to_force:
                    del host_map[(hostname, nodename)]
                else:
                    forced_hosts.append(hostname)
            if host_map:
                forced_hosts_str = ', '.join(forced_hosts)
                msg = _('Host filter forcing available hosts to %s')
            else:
                forced_hosts_str = ', '.join(hosts_to_force)
                msg = _("No hosts matched due to not matching "
                        "'force_hosts' value of '%s'")
            LOG.audit(msg % forced_hosts_str)

        def _match_forced_nodes(host_map, nodes_to_force):
            forced_nodes = []
            for (hostname, nodename) in host_map.keys():
                if nodename not in nodes_to_force:
                    del host_map[(hostname, nodename)]
                else:
                    forced_nodes.append(nodename)
            if host_map:
                forced_nodes_str = ', '.join(forced_nodes)
                msg = _('Host filter forcing available nodes to %s')
            else:
                forced_nodes_str = ', '.join(nodes_to_force)
                msg = _("No nodes matched due to not matching "
                        "'force_nodes' value of '%s'")
            LOG.audit(msg % forced_nodes_str)

        ignore_hosts = filter_properties.get('ignore_hosts', [])
        force_hosts = filter_properties.get('force_hosts', [])
        force_nodes = filter_properties.get('force_nodes', [])

        if ignore_hosts or force_hosts or force_nodes:
            # NOTE(deva): we can't assume "host" is unique because
            #             one host may have many nodes.
            name_to_cls_map = dict([((x.host, x.nodename), x) for x in hosts])
            if ignore_hosts:
                _strip_ignore_hosts(name_to_cls_map, ignore_hosts)
                if not name_to_cls_map:
                    return []
            # NOTE(deva): allow force_hosts and force_nodes independently
            if force_hosts:
                _match_forced_hosts(name_to_cls_map, force_hosts)
            if force_nodes:
                _match_forced_nodes(name_to_cls_map, force_nodes)
            hosts = name_to_cls_map.itervalues()

        return hosts

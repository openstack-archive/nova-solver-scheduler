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

from nova import exception
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova_solverscheduler.scheduler.solvers import constraints
from nova_solverscheduler.scheduler.solvers import utils as solver_utils

LOG = logging.getLogger(__name__)


class ServerGroupAffinityConstraint(constraints.BaseLinearConstraint):
    """Force to select hosts which host given server group."""

    def __init__(self, *args, **kwargs):
        super(ServerGroupAffinityConstraint, self).__init__(*args, **kwargs)
        self.policy_name = 'affinity'

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        context = filter_properties['context']
        scheduler_hints = filter_properties.get('scheduler_hints') or {}
        group_hint = scheduler_hints.get('group', None)

        policies = filter_properties.get('group_policies', [])
        if self.policy_name not in policies:
            return constraint_matrix

        group_hosts = filter_properties.get('group_hosts')

        # NOTE(xinyuan): the group hosts are already included in filter
        # properties, but we want to double check here to reduce possible
        # race conditions.
        try:
            group_hosts_sub = solver_utils.get_hosts_from_group_hint(
                    context, group_hint)
            if len(set(group_hosts_sub) - set(group_hosts)) > 0:
                raise ValueError(_('Group hosts value changed.'))
        except (exception.InstanceNotFound,
                exception.InstanceGroupNotFound,
                ValueError) as e:
            LOG.warn(_('Incomplete group host(s) information, rejected all '
                       'hosts. Reason: %(reason)s'), {'reason': str(e)})
            constraint_matrix = [[False for j in xrange(num_instances)]
                                for i in xrange(num_hosts)]
            return constraint_matrix

        LOG.debug(_('Group hosts: %(hosts)s.'),
                  {'hosts': ', '.join(group_hosts)})

        if not group_hosts:
            constraint_matrix = [
                    ([False for j in xrange(num_instances - 1)] + [True])
                    for i in xrange(num_hosts)]
        else:
            for i in xrange(num_hosts):
                if hosts[i].host not in group_hosts:
                    constraint_matrix[i] = [False for
                                            j in xrange(num_instances)]
                else:
                    LOG.debug(_('%(host)s is in group hosts.'),
                              {'host': hosts[i].host})

        return constraint_matrix


class ServerGroupAntiAffinityConstraint(constraints.BaseLinearConstraint):
    """Force to select hosts which host given server group."""

    def __init__(self, *args, **kwargs):
        super(ServerGroupAntiAffinityConstraint, self).__init__(
                                                            *args, **kwargs)
        self.policy_name = 'anti-affinity'

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        context = filter_properties['context']
        scheduler_hints = filter_properties.get('scheduler_hints') or {}
        group_hint = scheduler_hints.get('group', None)

        policies = filter_properties.get('group_policies', [])
        if self.policy_name not in policies:
            return constraint_matrix

        group_hosts = filter_properties.get('group_hosts')

        # NOTE(xinyuan): the group hosts are already included in filter
        # properties, but we want to double check here to reduce possible
        # race conditions.
        try:
            group_hosts_sub = solver_utils.get_hosts_from_group_hint(
                    context, group_hint)
            if len(set(group_hosts_sub) - set(group_hosts)) > 0:
                raise ValueError(_('Group hosts value changed.'))
        except (exception.InstanceNotFound,
                exception.InstanceGroupNotFound,
                ValueError) as e:
            LOG.warn(_('Incomplete group host(s) information, rejected all '
                       'hosts. Reason: %(reason)s'), {'reason': str(e)})
            constraint_matrix = [[False for j in xrange(num_instances)]
                                for i in xrange(num_hosts)]
            return constraint_matrix

        LOG.debug(_('Group hosts: %(hosts)s.'),
                  {'hosts': ', '.join(group_hosts)})

        for i in xrange(num_hosts):
            if hosts[i].host in group_hosts:
                constraint_matrix[i] = [False for j in xrange(num_instances)]
                LOG.debug(_('%(host)s is in group hosts.'),
                              {'host': hosts[i].host})
            else:
                constraint_matrix[i] = ([True] + [False for
                                        j in xrange(num_instances - 1)])

        return constraint_matrix

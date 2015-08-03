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

from oslo_log import log as logging

from nova_solverscheduler.scheduler.solvers import constraints

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

        policies = filter_properties.get('group_policies', [])
        if self.policy_name not in policies:
            return constraint_matrix

        group_hosts = filter_properties.get('group_hosts')

        LOG.debug('Group hosts: %(hosts)s.',
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
                    LOG.debug('%(host)s is in group hosts.',
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

        policies = filter_properties.get('group_policies', [])
        if self.policy_name not in policies:
            return constraint_matrix

        group_hosts = filter_properties.get('group_hosts')

        LOG.debug('Group hosts: %(hosts)s.',
                  {'hosts': ', '.join(group_hosts)})

        for i in xrange(num_hosts):
            if hosts[i].host in group_hosts:
                constraint_matrix[i] = [False for j in xrange(num_instances)]
                LOG.debug('%(host)s is in group hosts.',
                          {'host': hosts[i].host})
            else:
                constraint_matrix[i] = ([True] + [False for
                                        j in xrange(num_instances - 1)])

        return constraint_matrix

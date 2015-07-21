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

import six

from nova import exception
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler.filters import affinity_filter
from nova_solverscheduler.scheduler.solvers import constraints
from nova_solverscheduler.scheduler.solvers import utils as solver_utils

LOG = logging.getLogger(__name__)


class SameHostConstraint(constraints.BaseLinearConstraint):
    """Schedule the instance on the same host as another instance in a set
    of instances.
    """

    def __init__(self):
        super(SameHostConstraint, self).__init__()

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        context = filter_properties['context']
        elevated = context.elevated()
        scheduler_hints = filter_properties.get('scheduler_hints') or {}
        affinity_uuids = scheduler_hints.get('same_host', [])

        if not affinity_uuids:
            return constraint_matrix

        if isinstance(affinity_uuids, six.string_types):
            affinity_uuids = [affinity_uuids]

        # get hosts of given instances
        try:
            affinity_hosts = solver_utils.get_hosts_from_instance_uuids(
                    elevated, affinity_uuids)
            LOG.debug(_('Affinity hosts: %(hosts)s.'),
                      {'hosts': ', '.join(affinity_hosts)})
        except (exception.InstanceNotFound, ValueError) as e:
            LOG.warn(_('Incomplete affinity host(s) information, rejected all '
                       'hosts. Reason: %(reason)s'), {'reason': str(e)})
            constraint_matrix = [[False for j in xrange(num_instances)]
                                for i in xrange(num_hosts)]
            return constraint_matrix

        for i in xrange(num_hosts):
            host_name = hosts[i].host
            if host_name in affinity_hosts:
                LOG.debug(_('%(host)s passed same-host check.'),
                          {'host': host_name})
            else:
                constraint_matrix[i] = [False for j in xrange(num_instances)]

        return constraint_matrix


class DifferentHostConstraint(constraints.BaseLinearConstraint):
    """Schedule the instance on a different host from a set of instances."""

    def __init__(self):
        super(DifferentHostConstraint, self).__init__()

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        context = filter_properties['context']
        elevated = context.elevated()
        scheduler_hints = filter_properties.get('scheduler_hints') or {}
        affinity_uuids = scheduler_hints.get('different_host', [])

        if not affinity_uuids:
            return constraint_matrix

        if isinstance(affinity_uuids, six.string_types):
            affinity_uuids = [affinity_uuids]

        # get hosts of given instances
        try:
            affinity_hosts = solver_utils.get_hosts_from_instance_uuids(
                    elevated, affinity_uuids)
            LOG.debug(_('Affinity hosts: %(hosts)s.'),
                      {'hosts': ', '.join(affinity_hosts)})
        except (exception.InstanceNotFound, ValueError) as e:
            LOG.warn(_('Incomplete affinity host(s) information, rejected all '
                       'hosts. Reason: %(reason)s'), {'reason': str(e)})
            constraint_matrix = [[False for j in xrange(num_instances)]
                                for i in xrange(num_hosts)]
            return constraint_matrix

        for i in xrange(num_hosts):
            host_name = hosts[i].host
            if host_name in affinity_hosts:
                constraint_matrix[i] = [False for j in xrange(num_instances)]
                LOG.debug(_('%(host)s didnot pass different-host check.'),
                          {'host': host_name})

        return constraint_matrix


class SimpleCidrAffinityConstraint(constraints.BaseFilterConstraint):
    """Schedule the instance on a host with a particular cidr."""
    host_filter_cls = affinity_filter.SimpleCIDRAffinityFilter

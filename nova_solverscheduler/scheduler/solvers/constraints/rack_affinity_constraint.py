# Copyright (c) 2015 Cisco Systems, Inc.
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

from oslo_log import log as logging

from nova.compute import api as compute
from nova import db
from nova.i18n import _
from nova_solverscheduler.scheduler.solvers import constraints
from nova_solverscheduler.scheduler.solvers import utils as solver_utils

LOG = logging.getLogger(__name__)


class SameRackConstraint(constraints.BaseLinearConstraint):
    """Place instances in the same racks as those of specified instances.
    If the specified instances are in hosts without rack config, then place
    instances in the same hosts as those of specified instances.
    """

    def __init__(self):
        super(SameRackConstraint, self).__init__()
        self.compute_api = compute.API()

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        context = filter_properties['context']
        elevated = context.elevated()
        scheduler_hints = filter_properties.get('scheduler_hints') or {}
        affinity_uuids = scheduler_hints.get('same_rack', [])

        if not affinity_uuids:
            return constraint_matrix

        if isinstance(affinity_uuids, six.string_types):
            affinity_uuids = [affinity_uuids]

        host_racks_map = db.aggregate_host_get_by_metadata_key(elevated,
                                                                key='rack')
        if not host_racks_map:
            # try load from external source
            host_racks_map = solver_utils.get_host_racks_config()

        affinity_racks = set([])
        affinity_hosts = set([])

        for i in xrange(num_hosts):
            host_name = hosts[i].host
            host_racks = host_racks_map.get(host_name, set([]))
            if self.compute_api.get_all(context,
                                        {'host': host_name,
                                        'uuid': affinity_uuids,
                                        'deleted': False}):
                affinity_racks = affinity_racks.union(host_racks)
                affinity_hosts.add(host_name)

        for i in xrange(num_hosts):
            host_name = hosts[i].host
            host_racks = host_racks_map.get(host_name, set([]))
            if host_name in affinity_hosts:
                LOG.debug(_("%(host)s passed same-rack check."),
                        {'host': host_name})
                continue
            elif (len(host_racks) == 0) or any([rack not in affinity_racks
                                                for rack in host_racks]):
                constraint_matrix[i] = [False for j in xrange(num_instances)]
            else:
                LOG.debug(_("%(host)s passed same-rack check."),
                        {'host': host_name})

        return constraint_matrix


class DifferentRackConstraint(constraints.BaseLinearConstraint):
    """Place instances in different racks as those of specified instances.
    If the specified instances are in hosts without rack config, then place
    instances in different hosts as those of specified instances.
    """

    def __init__(self):
        super(DifferentRackConstraint, self).__init__()
        self.compute_api = compute.API()

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        context = filter_properties['context']
        elevated = context.elevated()
        scheduler_hints = filter_properties.get('scheduler_hints') or {}
        affinity_uuids = scheduler_hints.get('different_rack', [])

        if not affinity_uuids:
            return constraint_matrix

        if isinstance(affinity_uuids, six.string_types):
            affinity_uuids = [affinity_uuids]

        host_racks_map = db.aggregate_host_get_by_metadata_key(elevated,
                                                                key='rack')
        if not host_racks_map:
            # try load from external source
            host_racks_map = solver_utils.get_host_racks_config()

        affinity_racks = set([])
        affinity_hosts = set([])

        for i in xrange(num_hosts):
            host_name = hosts[i].host
            host_racks = host_racks_map.get(host_name, set([]))
            if self.compute_api.get_all(context,
                                        {'host': host_name,
                                        'uuid': affinity_uuids,
                                        'deleted': False}):
                affinity_racks = affinity_racks.union(host_racks)
                affinity_hosts.add(host_name)

        for i in xrange(num_hosts):
            host_name = hosts[i].host
            host_racks = host_racks_map.get(host_name, set([]))
            if any([rack in affinity_racks for rack in host_racks]) or (
                    host_name in affinity_hosts):
                constraint_matrix[i] = [False for j in xrange(num_instances)]
                LOG.debug(_("%(host)s didnot pass different-rack check."),
                        {'host': host_name})

        return constraint_matrix

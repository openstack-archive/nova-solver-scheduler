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

from oslo_config import cfg
from oslo_log import log as logging

from nova.i18n import _
from nova_solverscheduler.scheduler.solvers import costs as solver_costs
from nova_solverscheduler.scheduler.solvers import utils as solver_utils

affinity_cost_opts = [
        cfg.FloatOpt('affinity_cost_multiplier',
                     default=1.0,
                     help='Multiplier used for affinity cost. Must be a '
                          'positive number.'),
        cfg.FloatOpt('anti_affinity_cost_multiplier',
                     default=1.0,
                     help='Multiplier used for anti-affinity cost. Must be '
                          'a positive number.'),
]

CONF = cfg.CONF
CONF.register_opts(affinity_cost_opts, group='solver_scheduler')

LOG = logging.getLogger(__name__)


class AffinityCost(solver_costs.BaseLinearCost):

    def __init__(self):
        super(AffinityCost, self).__init__()

    def cost_multiplier(self):
        return CONF.solver_scheduler.affinity_cost_multiplier

    def get_extended_cost_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        multiplier = self.cost_multiplier()
        if multiplier == 0:
            extended_cost_matrix = [[0 for j in xrange(num_instances + 1)]
                                    for i in xrange(num_hosts)]
            return extended_cost_matrix

        scheduler_hints = filter_properties.get('scheduler_hints') or {}
        affinity_uuids = scheduler_hints.get('soft_same_host', [])

        if affinity_uuids == '':
            extended_cost_matrix = [[float(-j) / multiplier
                                    for j in xrange(num_instances + 1)]
                                    for i in xrange(num_hosts)]
            LOG.debug(_('No instance specified for AffinityCost.'))
            return extended_cost_matrix

        if isinstance(affinity_uuids, six.string_types):
            affinity_uuids = [affinity_uuids]

        if affinity_uuids:
            extended_cost_matrix = [[1 - (float(j) / multiplier)
                                    for j in xrange(num_instances + 1)]
                                    for i in xrange(num_hosts)]
            for i in xrange(num_hosts):
                if solver_utils.instance_uuids_overlap(hosts[i],
                                                       affinity_uuids):
                    extended_cost_matrix[i] = [float(-j) / multiplier for j in
                                                    xrange(num_instances + 1)]
        else:
            extended_cost_matrix = [[0 for j in xrange(num_instances + 1)]
                                    for i in xrange(num_hosts)]

        return extended_cost_matrix


class AntiAffinityCost(solver_costs.BaseLinearCost):

    def __init__(self):
        super(AntiAffinityCost, self).__init__()

    def cost_multiplier(self):
        return CONF.solver_scheduler.anti_affinity_cost_multiplier

    def get_extended_cost_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        multiplier = self.cost_multiplier()
        if multiplier == 0:
            extended_cost_matrix = [[0 for j in xrange(num_instances + 1)]
                                    for i in xrange(num_hosts)]
            return extended_cost_matrix

        scheduler_hints = filter_properties.get('scheduler_hints') or {}
        affinity_uuids = scheduler_hints.get('soft_different_host', [])

        if affinity_uuids == '':
            extended_cost_matrix = [[float(j) / multiplier
                                    for j in xrange(num_instances + 1)]
                                    for i in xrange(num_hosts)]
            LOG.debug(_('No instance specified for AntiAffinityCost.'))
            return extended_cost_matrix

        if isinstance(affinity_uuids, six.string_types):
            affinity_uuids = [affinity_uuids]

        if affinity_uuids:
            extended_cost_matrix = [[float(j) / multiplier
                                    for j in xrange(num_instances + 1)]
                                    for i in xrange(num_hosts)]
            for i in xrange(num_hosts):
                if solver_utils.instance_uuids_overlap(hosts[i],
                                                       affinity_uuids):
                    extended_cost_matrix[i] = [1 + (float(j) / multiplier)
                                        for j in xrange(num_instances + 1)]
        else:
            extended_cost_matrix = [[0 for j in xrange(num_instances + 1)]
                                    for i in xrange(num_hosts)]

        return extended_cost_matrix

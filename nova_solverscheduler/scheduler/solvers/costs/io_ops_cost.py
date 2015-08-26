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

"""
IO Ops Cost.  Calculate instance placement costs by hosts' IO ops numbers.

The default is to preferably choose light workload compute hosts. If you prefer
choosing heavy workload compute hosts, you can set 'io_ops_cost_multiplier'
option to a negative number and the cost has the opposite effect of the
default.
"""

from oslo_config import cfg

from nova_solverscheduler.scheduler.solvers import costs as solver_costs
from nova_solverscheduler.scheduler.solvers.costs import utils

io_ops_cost_opts = [
        cfg.FloatOpt('io_ops_cost_multiplier',
                     default=1.0,
                     help='Multiplier used for io ops cost. Negative '
                          'numbers mean to stack vs spread.'),
]

CONF = cfg.CONF
CONF.register_opts(io_ops_cost_opts, group='solver_scheduler')


class IoOpsCost(solver_costs.BaseLinearCost):

    def cost_multiplier(self):
        return CONF.solver_scheduler.io_ops_cost_multiplier

    def get_extended_cost_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        extended_cost_matrix = [
                [hosts[i].num_io_ops + j for j in xrange(num_instances + 1)]
                for i in xrange(num_hosts)]
        extended_cost_matrix = utils.normalize_cost_matrix(
                                                        extended_cost_matrix)
        return extended_cost_matrix

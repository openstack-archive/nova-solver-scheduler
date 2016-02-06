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

"""
Metrics Cost.  Calculate hosts' costs by their metrics.

This can compute the costs based on the compute node hosts' various
metrics. The to-be computed metrics and their weighing ratio are specified
in the configuration file as the followings:

    [metrics]
    weight_setting = name1=1.0, name2=-1.0

    The final weight would be name1.value * 1.0 + name2.value * -1.0.
"""

from oslo_config import cfg

from nova.scheduler import utils
from nova_solverscheduler.scheduler.solvers import costs as solver_costs
from nova_solverscheduler.scheduler.solvers.costs import utils as cost_utils

metrics_cost_opts = [
    cfg.FloatOpt('metrics_cost_multiplier',
                 default=1.0,
                 help='Multiplier used for metrics costs.'),
]

metrics_weight_opts = [
    cfg.FloatOpt('weight_multiplier_of_unavailable',
                 default=(-1.0),
                 help='If any one of the metrics set by weight_setting '
                      'is unavailable, the metric weight of the host '
                      'will be set to (minw + (maxw - minw) * m), '
                      'where maxw and minw are the max and min weights '
                      'among all hosts, and m is the multiplier.'),
]

CONF = cfg.CONF
CONF.register_opts(metrics_cost_opts, group='solver_scheduler')
CONF.register_opts(metrics_weight_opts, group='metrics')
CONF.import_opt('weight_setting', 'nova.scheduler.weights.metrics',
                group='metrics')


class MetricsCost(solver_costs.BaseLinearCost):

    def __init__(self):
        self._parse_setting()

    def _parse_setting(self):
        self.setting = utils.parse_options(CONF.metrics.weight_setting,
                                           sep='=',
                                           converter=float,
                                           name="metrics.weight_setting")

    def cost_multiplier(self):
        return CONF.solver_scheduler.metrics_cost_multiplier

    def get_extended_cost_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        host_weights = []
        numeric_values = []
        for host in hosts:
            metric_sum = 0.0
            for (name, ratio) in self.setting:
                metric = host.metrics.get(name, None)
                if metric:
                    metric_sum += metric.value * ratio
                else:
                    metric_sum = None
                    break
            host_weights.append(metric_sum)
            if metric_sum:
                numeric_values.append(metric_sum)
        if numeric_values:
            minval = min(numeric_values)
            maxval = max(numeric_values)
            weight_of_unavailable = (minval + (maxval - minval) *
                                     CONF.metrics.weight_multiplier_of_unavailable)
            for i in range(num_hosts):
                if host_weights[i] is None:
                    host_weights[i] = weight_of_unavailable
        else:
            host_weights = [0 for i in xrange(num_hosts)]

        extended_cost_matrix = [[(-host_weights[i])
                                for j in xrange(num_instances + 1)]
                                for i in xrange(num_hosts)]
        extended_cost_matrix = cost_utils.normalize_cost_matrix(
            extended_cost_matrix)
        return extended_cost_matrix

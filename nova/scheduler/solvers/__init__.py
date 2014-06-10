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
Scheduler host constraint solvers
"""

from nova.scheduler.solvers import costs
from nova.scheduler.solvers import linearconstraints

from oslo.config import cfg

scheduler_solver_costs_opt = cfg.ListOpt(
        'scheduler_solver_costs',
        default=['RamCost'],
        help='Which cost matrices to use in the scheduler solver.')

# (xinyuan) This option should be changed to DictOpt type
# when bug #1276859 is fixed.
scheduler_solver_cost_weights_opt = cfg.ListOpt(
        'scheduler_solver_cost_weights',
        default=['RamCost:1.0'],
        help='Assign weight for each cost')

scheduler_solver_constraints_opt = cfg.ListOpt(
        'scheduler_solver_constraints',
        default=[],
        help='Which constraints to use in scheduler solver')

CONF = cfg.CONF
CONF.register_opt(scheduler_solver_costs_opt, group='solver_scheduler')
CONF.register_opt(scheduler_solver_cost_weights_opt, group='solver_scheduler')
CONF.register_opt(scheduler_solver_constraints_opt, group='solver_scheduler')
SOLVER_CONF = CONF.solver_scheduler


class BaseHostSolver(object):
    """Base class for host constraint solvers."""

    def _get_cost_classes(self):
        """Get cost classes from configuration."""
        cost_classes = []
        cost_handler = costs.CostHandler()
        all_cost_classes = cost_handler.get_all_classes()
        expected_costs = SOLVER_CONF.scheduler_solver_costs
        for cost in all_cost_classes:
            if cost.__name__ in expected_costs:
                cost_classes.append(cost)
        return cost_classes

    def _get_constraint_classes(self):
        """Get constraint classes from configuration."""
        constraint_classes = []
        constraint_handler = linearconstraints.LinearConstraintHandler()
        all_constraint_classes = constraint_handler.get_all_classes()
        expected_constraints = SOLVER_CONF.scheduler_solver_constraints
        for constraint in all_constraint_classes:
            if constraint.__name__ in expected_constraints:
                constraint_classes.append(constraint)
        return constraint_classes

    def _get_cost_weights(self):
        """Get cost weights from configuration."""
        cost_weights = {}
        # (xinyuan) This is a temporary workaround for bug #1276859,
        # need to wait until DictOpt is supported by config sample generator.
        weights_str_list = SOLVER_CONF.scheduler_solver_cost_weights
        for weight_str in weights_str_list:
            (key, sep, val) = weight_str.partition(':')
            cost_weights[str(key)] = float(val)
        return cost_weights

    def host_solve(self, hosts, instance_uuids, request_spec,
                   filter_properties):
        """Return the list of host-instance tuples after
           solving the constraints.
           Implement this in a subclass.
        """
        raise NotImplementedError()

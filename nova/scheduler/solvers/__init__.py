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
Scheduler host constraint solvers
"""

from oslo.config import cfg

from nova.scheduler.solvers import costs
from nova.scheduler.solvers import linearconstraints


scheduler_solver_costs_opt = cfg.ListOpt(
        'scheduler_solver_costs',
        default=['nova.scheduler.solvers.costs.ram_cost.RamCost'],
        help='Which cost matrices to use in the scheduler solver.')

scheduler_solver_cost_weights_opt = cfg.DictOpt(
        'scheduler_solver_cost_weights',
        default={'RamCost':1.0},
        help='Assign weight for each cost')

scheduler_solver_constraints_opt = cfg.ListOpt(
        'scheduler_solver_constraints',
        default=[],
        help='Which constraints to use in scheduler solver')

CONF = cfg.CONF
CONF.register_opt(scheduler_solver_costs_opt)
CONF.register_opt(scheduler_solver_cost_weights_opt)
CONF.register_opt(scheduler_solver_constraints_opt)


class BaseHostSolver(object):
    """Base class for host constraint solvers."""

    def _get_cost_classes(self):
        # Get cost classes.
        cost_classes = []
        cost_handler = costs.CostHandler()
        all_cost_classes = cost_handler.get_all_classes()
        for costName in CONF.scheduler_solver_costs:
            for costCls in all_cost_classes:
                if costCls.__name__ == costName:
                    cost_classes.append(costCls)
        return cost_classes
    
    def _get_constraint_classes(self):
        # Get constraint classes.
        constraint_classes = []
        constraint_handler = linearconstraints.LinearConstraintHandler()
        all_constraint_classes = constraint_handler.get_all_classes()
        for constraintName in CONF.scheduler_solver_constraints:
            for constraintCls in all_constraint_classes:
                if constraintCls.__name__ == constraintName:
                    constraint_classes.append(constraintCls)
        return constraint_classes
    
    def _get_cost_weights(self):
        # Get cost weights.
        cost_weights = CONF.scheduler_solver_cost_weights
        return cost_weights
    
    def host_solve(self, hosts, instance_uuids, request_spec,
                   filter_properties):
        """Return the list of host-instance tuples after
           solving the constraints.
           Implement this in a subclass.
        """
        raise NotImplementedError()

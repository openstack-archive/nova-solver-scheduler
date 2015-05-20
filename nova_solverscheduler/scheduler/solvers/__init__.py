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

from oslo_config import cfg

from nova_solverscheduler.scheduler.solvers import constraints
from nova_solverscheduler.scheduler.solvers import costs
from nova_solverscheduler import solver_scheduler_exception as exception

scheduler_solver_opts = [
        cfg.ListOpt('scheduler_solver_costs',
                    default=['RamCost'],
                    help='Which cost matrices to use in the '
                         'scheduler solver.'),
        cfg.ListOpt('scheduler_solver_constraints',
                    default=['ActiveHostsConstraint'],
                    help='Which constraints to use in scheduler solver'),
]

CONF = cfg.CONF
CONF.register_opts(scheduler_solver_opts, group='solver_scheduler')


class BaseHostSolver(object):
    """Base class for host constraint solvers."""

    def __init__(self):
        super(BaseHostSolver, self).__init__()

    def _get_cost_classes(self):
        """Get cost classes from configuration."""
        cost_classes = []
        bad_cost_names = []
        cost_handler = costs.CostHandler()
        all_cost_classes = cost_handler.get_all_classes()
        all_cost_names = [c.__name__ for c in all_cost_classes]
        expected_costs = CONF.solver_scheduler.scheduler_solver_costs
        for cost in expected_costs:
            if cost in all_cost_names:
                cost_classes.append(all_cost_classes[
                                                all_cost_names.index(cost)])
            else:
                bad_cost_names.append(cost)
        if bad_cost_names:
            msg = ", ".join(bad_cost_names)
            raise exception.SchedulerSolverCostNotFound(cost_name=msg)
        return cost_classes

    def _get_constraint_classes(self):
        """Get constraint classes from configuration."""
        constraint_classes = []
        bad_constraint_names = []
        constraint_handler = constraints.ConstraintHandler()
        all_constraint_classes = constraint_handler.get_all_classes()
        all_constraint_names = [c.__name__ for c in all_constraint_classes]
        expected_constraints = (
                CONF.solver_scheduler.scheduler_solver_constraints)
        for constraint in expected_constraints:
            if constraint in all_constraint_names:
                constraint_classes.append(all_constraint_classes[
                                    all_constraint_names.index(constraint)])
            else:
                bad_constraint_names.append(constraint)
        if bad_constraint_names:
            msg = ", ".join(bad_constraint_names)
            raise exception.SchedulerSolverConstraintNotFound(
                                                        constraint_name=msg)
        return constraint_classes

    def solve(self, hosts, filter_properties):
        """Return the list of host-instance tuples after
           solving the constraints.
           Implement this in a subclass.
        """
        raise NotImplementedError()

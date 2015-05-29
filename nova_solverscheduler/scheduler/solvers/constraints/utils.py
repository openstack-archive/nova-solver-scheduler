# Copyright (c) 2015 Cisco Systems Inc.
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

from oslo.config import cfg

CONF = cfg.CONF

CONF.import_opt('scheduler_solver_constraints',
        'nova_solverscheduler.scheduler.solvers', group='solver_scheduler')


def validate_constraint(constraint):
    """Validates that the constraint is configured in nova configuration."""
    return constraint in CONF.solver_scheduler.scheduler_solver_constraints

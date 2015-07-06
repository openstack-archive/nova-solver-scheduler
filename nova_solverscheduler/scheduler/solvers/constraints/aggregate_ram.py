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

from oslo_config import cfg
from oslo_log import log as logging

from nova.i18n import _LW
from nova_solverscheduler.scheduler.solvers.constraints import ram_constraint
from nova_solverscheduler.scheduler.solvers import utils

CONF = cfg.CONF
CONF.import_opt('ram_allocation_ratio', 'nova.scheduler.filters.ram_filter')

LOG = logging.getLogger(__name__)


class AggregateRamConstraint(ram_constraint.RamConstraint):
    """AggregateRamConstraint with per-aggregate ram subscription flag.

    Fall back to global ram_allocation_ratio if no per-aggregate setting found.
    """

    def _get_ram_allocation_ratio(self, host_state, filter_properties):
        aggregate_vals = utils.aggregate_values_from_key(
                host_state, 'ram_allocation_ratio')

        try:
            ratio = utils.validate_num_values(
                    aggregate_vals, CONF.ram_allocation_ratio, cast_to=float)
        except ValueError as e:
            LOG.warning(_LW("Could not decode ram_allocation_ratio: '%s'"), e)
            ratio = CONF.ram_allocation_ratio

        return ratio

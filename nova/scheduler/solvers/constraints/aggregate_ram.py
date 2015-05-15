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

from oslo.config import cfg

from nova import db
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler.solvers.constraints import ram_constraint

CONF = cfg.CONF
CONF.import_opt('ram_allocation_ratio', 'nova.scheduler.filters.ram_filter')

LOG = logging.getLogger(__name__)


class AggregateRamConstraint(ram_constraint.RamConstraint):
    """AggregateRamConstraint with per-aggregate ram subscription flag.

    Fall back to global ram_allocation_ratio if no per-aggregate setting found.
    """

    def _get_ram_allocation_ratio(self, host_state, filter_properties):
        context = filter_properties['context'].elevated()
        # TODO(uni): DB query in filter is a performance hit, especially for
        # system with lots of hosts. Will need a general solution here to fix
        # all filters with aggregate DB call things.
        metadata = db.aggregate_metadata_get_by_host(
                     context, host_state.host, key='ram_allocation_ratio')
        aggregate_vals = metadata.get('ram_allocation_ratio', set())
        num_values = len(aggregate_vals)

        if num_values == 0:
            return CONF.ram_allocation_ratio

        if num_values > 1:
            LOG.warn(_("%(num_values)d ratio values found, "
                        "of which the minimum value will be used."),
                        {'num_values': num_values})

        try:
            ratio = min(map(float, aggregate_vals))
        except ValueError as e:
            LOG.warning(_("Could not decode ram_allocation_ratio: '%s'"), e)
            ratio = CONF.ram_allocation_ratio

        return ratio

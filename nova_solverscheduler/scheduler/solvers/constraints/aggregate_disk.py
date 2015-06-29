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

from nova import db
from nova.i18n import _LW
from nova_solverscheduler.scheduler.solvers.constraints import disk_constraint

CONF = cfg.CONF
CONF.import_opt('disk_allocation_ratio', 'nova.scheduler.filters.disk_filter')

LOG = logging.getLogger(__name__)


class AggregateDiskConstraint(disk_constraint.DiskConstraint):
    """AggregateDiskConstraint with per-aggregate disk subscription flag.

    Fall back to global disk_allocation_ratio if no per-aggregate setting
    found.
    """

    def _get_disk_allocation_ratio(self, host_state, filter_properties):
        context = filter_properties['context'].elevated()
        # TODO(uni): DB query in filter is a performance hit, especially for
        # system with lots of hosts. Will need a general solution here to fix
        # all filters with aggregate DB call things.
        metadata = db.aggregate_metadata_get_by_host(
                     context, host_state.host, key='disk_allocation_ratio')
        aggregate_vals = metadata.get('disk_allocation_ratio', set())
        num_values = len(aggregate_vals)

        if num_values == 0:
            return CONF.disk_allocation_ratio

        if num_values > 1:
            LOG.warn(_LW("%(num_values)d ratio values found, "
                        "of which the minimum value will be used."),
                        {'num_values': num_values})

        try:
            ratio = min(map(float, aggregate_vals))
        except ValueError as e:
            LOG.warning(_LW("Could not decode disk_allocation_ratio: '%s'"), e)
            ratio = CONF.disk_allocation_ratio

        return ratio

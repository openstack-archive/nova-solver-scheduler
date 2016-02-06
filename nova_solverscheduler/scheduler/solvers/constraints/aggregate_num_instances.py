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

from oslo_config import cfg
from oslo_log import log as logging

from nova.i18n import _LW
from nova_solverscheduler.scheduler.solvers.constraints \
    import num_instances_constraint
from nova_solverscheduler.scheduler.solvers import utils

CONF = cfg.CONF
CONF.import_opt('max_instances_per_host',
                'nova.scheduler.filters.num_instances_filter')

LOG = logging.getLogger(__name__)


class AggregateNumInstancesConstraint(
        num_instances_constraint.NumInstancesConstraint):

    """AggregateNumInstancesConstraint with per-aggregate max num instances
    per host.

    Fall back to global max_instances_per_host if no per-aggregate setting
    found.
    """

    def _get_max_instances_per_host(self, host_state, filter_properties):
        aggregate_vals = utils.aggregate_values_from_key(
            host_state, 'max_instances_per_host')

        try:
            value = utils.validate_num_values(
                aggregate_vals, CONF.max_instances_per_host, cast_to=int)
        except ValueError as e:
            LOG.warning(_LW("Could not decode max_instances_per_host: '%s'"),
                        e)
            value = CONF.max_instances_per_host

        return value

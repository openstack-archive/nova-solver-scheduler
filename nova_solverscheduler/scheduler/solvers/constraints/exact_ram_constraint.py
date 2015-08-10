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


from oslo_log import log as logging

from nova.i18n import _LW
from nova_solverscheduler.scheduler.solvers import constraints

LOG = logging.getLogger(__name__)


class ExactRamConstraint(constraints.BaseLinearConstraint):
    """Constraint that selects hosts with exact amount of RAM available."""

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        # get requested ram
        instance_type = filter_properties.get('instance_type') or {}
        requested_ram = instance_type.get('memory_mb', 0)
        if 'memory_mb' not in instance_type:
            LOG.warn(_LW("No information about requested instances\' RAM size "
                    "was found, default value (0) is used."))
        if requested_ram <= 0:
            LOG.warn(_LW("ExactRamConstraint is skipped because requested "
                        "instance RAM size is 0 or invalid."))
            return constraint_matrix

        for i in xrange(num_hosts):
            if requested_ram == hosts[i].free_ram_mb:
                constraint_matrix[i] = (
                        [True] + [False for j in xrange(num_instances - 1)])
            else:
                constraint_matrix[i] = [False for j in xrange(num_instances)]
                LOG.debug("%(host)s does not have exactly %(requested_ram)s MB"
                          "RAM, it has %(usable_ram)s MB RAM.",
                          {'host': hosts[i],
                           'requested_ram': requested_ram,
                           'usable_ram': hosts[i].free_ram_mb})

        return constraint_matrix

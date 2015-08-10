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


class ExactDiskConstraint(constraints.BaseLinearConstraint):
    """Constraint that selects hosts with exact amount of disk space."""

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        # get requested disk
        instance_type = filter_properties.get('instance_type') or {}
        requested_disk = (1024 * (instance_type.get('root_gb', 0) +
                                  instance_type.get('ephemeral_gb', 0)) +
                                  instance_type.get('swap', 0))
        for inst_type_key in ['root_gb', 'ephemeral_gb', 'swap']:
            if inst_type_key not in instance_type:
                LOG.warn(_LW("Disk information of requested instances\' %s "
                        "is incomplete, use 0 as the requested size."),
                        inst_type_key)
        if requested_disk <= 0:
            LOG.warn(_LW("ExactDiskConstraint is skipped because requested "
                        "instance disk size is 0 or invalid."))
            return constraint_matrix

        for i in xrange(num_hosts):
            if requested_disk == hosts[i].free_disk_mb:
                constraint_matrix[i] = (
                        [True] + [False for j in xrange(num_instances - 1)])
            else:
                constraint_matrix[i] = [False for j in xrange(num_instances)]
                LOG.debug("%(host)s does not have exactly %(requested_disk)s "
                          "MB disk, it has %(usable_disk)s MB disk.",
                          {'host': hosts[i],
                           'requested_disk': requested_disk,
                           'usable_disk': hosts[i].free_disk_mb})

        return constraint_matrix

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
from nova_solverscheduler.scheduler.solvers import constraints

CONF = cfg.CONF
CONF.import_opt('disk_allocation_ratio', 'nova.scheduler.filters.disk_filter')

LOG = logging.getLogger(__name__)


class DiskConstraint(constraints.BaseLinearConstraint):
    """Constraint of the maximum total disk demand acceptable on each host."""

    def _get_disk_allocation_ratio(self, host_state, filter_properties):
        return CONF.disk_allocation_ratio

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
            LOG.warn(_LW("DiskConstraint is skipped because requested "
                        "instance disk size is 0 or invalid."))
            return constraint_matrix

        for i in xrange(num_hosts):
            disk_allocation_ratio = self._get_disk_allocation_ratio(
                                                hosts[i], filter_properties)
            # get usable disk
            free_disk_mb = hosts[i].free_disk_mb
            total_usable_disk_mb = hosts[i].total_usable_disk_gb * 1024
            disk_mb_limit = total_usable_disk_mb * disk_allocation_ratio
            used_disk_mb = total_usable_disk_mb - free_disk_mb
            usable_disk_mb = disk_mb_limit - used_disk_mb

            acceptable_num_instances = int(usable_disk_mb / requested_disk)
            if acceptable_num_instances < num_instances:
                inacceptable_num = (num_instances - acceptable_num_instances)
                constraint_matrix[i] = (
                        [True for j in xrange(acceptable_num_instances)] +
                        [False for j in xrange(inacceptable_num)])

            LOG.debug("%(host)s can accept %(num)s requested instances "
                        "according to DiskConstraint.",
                        {'host': hosts[i],
                        'num': acceptable_num_instances})

            disk_gb_limit = disk_mb_limit / 1024
            hosts[i].limits['disk_gb'] = disk_gb_limit

        return constraint_matrix

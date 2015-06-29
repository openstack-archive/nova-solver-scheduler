# Copyright (c) 2011-2012 OpenStack Foundation
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

import copy

from oslo_log import log as logging

from nova.i18n import _LW
from nova_solverscheduler.scheduler.solvers import constraints

LOG = logging.getLogger(__name__)


class PciPassthroughConstraint(constraints.BaseLinearConstraint):
    """Constraint that schedules instances on a host if the host has devices
    to meet the device requests in the 'extra_specs' for the flavor.

    PCI resource tracker provides updated summary information about the
    PCI devices for each host, like:
    [{"count": 5, "vendor_id": "8086", "product_id": "1520",
        "extra_info":'{}'}],
    and VM requests PCI devices via PCI requests, like:
    [{"count": 1, "vendor_id": "8086", "product_id": "1520",}].

    The constraint checks if the host passes or not based on this information.
    """

    def _get_acceptable_pci_requests_times(self, max_times_to_try,
                                                pci_requests, host_pci_stats):
        acceptable_times = 0
        while acceptable_times < max_times_to_try:
            if host_pci_stats.support_requests(pci_requests):
                acceptable_times += 1
                host_pci_stats.apply_requests(pci_requests)
            else:
                break
        return acceptable_times

    def get_constraint_matrix(self, hosts, filter_properties):
        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                            for i in xrange(num_hosts)]

        pci_requests = filter_properties.get('pci_requests')
        if not pci_requests:
            LOG.warn(_LW("PciPassthroughConstraint check is skipped because "
                        "requested instance PCI requests is unavailable."))
            return constraint_matrix

        for i in xrange(num_hosts):
            host_pci_stats = copy.deepcopy(hosts[i].pci_stats)
            acceptable_num_instances = (
                    self._get_acceptable_pci_requests_times(num_instances,
                                                pci_requests, host_pci_stats))

            if acceptable_num_instances < num_instances:
                inacceptable_num = num_instances - acceptable_num_instances
                constraint_matrix[i] = (
                        [True for j in xrange(acceptable_num_instances)] +
                        [False for j in xrange(inacceptable_num)])

            LOG.debug("%(host)s can accept %(num)s requested instances "
                        "according to PciPassthroughConstraint.",
                        {'host': hosts[i],
                        'num': acceptable_num_instances})

        return constraint_matrix

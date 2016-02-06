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

from nova_solverscheduler.scheduler.solvers import constraints

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('max_io_ops_per_host', 'nova.scheduler.filters.io_ops_filter')


class IoOpsConstraint(constraints.BaseLinearConstraint):

    """A constraint to ensure only those hosts are selected whose number of
    concurrent I/O operations are within a set threshold.
    """

    def get_constraint_matrix(self, hosts, filter_properties):
        max_io_ops = CONF.max_io_ops_per_host

        num_hosts = len(hosts)
        num_instances = filter_properties.get('num_instances')

        constraint_matrix = [[True for j in xrange(num_instances)]
                             for i in xrange(num_hosts)]

        for i in xrange(num_hosts):
            num_io_ops = hosts[i].num_io_ops

            acceptable_num_instances = int(max_io_ops - num_io_ops)
            if acceptable_num_instances < 0:
                acceptable_num_instances = 0
            if acceptable_num_instances < num_instances:
                inacceptable_num = (num_instances - acceptable_num_instances)
                constraint_matrix[i] = (
                    [True for j in xrange(acceptable_num_instances)] +
                    [False for j in xrange(inacceptable_num)])

            LOG.debug("%(host)s can accept %(num)s requested instances "
                      "according to IoOpsConstraint.",
                      {'host': hosts[i],
                       'num': acceptable_num_instances})

        return constraint_matrix

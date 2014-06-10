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

from nova.compute import api as compute
from nova import db
from nova.openstack.common import log as logging
from nova.scheduler.solvers import linearconstraints

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
CONF.import_opt('default_availability_zone', 'nova.availability_zones')


class AvailabilityZoneConstraint(linearconstraints.BaseLinearConstraint):
    """To select only the hosts belonging to an availability zone.
    """

    def __init__(self, variables, hosts, instance_uuids, request_spec,
                filter_properties):
        self.compute_api = compute.API()
        [self.num_hosts, self.num_instances] = self._get_host_instance_nums(
                                        hosts, instance_uuids, request_spec)

    def _get_host_instance_nums(self, hosts, instance_uuids, request_spec):
        """This method calculates number of hosts and instances."""
        num_hosts = len(hosts)
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
        return [num_hosts, num_instances]

    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) constant_vector
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the constant_vector is merged into left-hand-side,
    # thus the right-hand-side is always 0.

    def get_coefficient_vectors(self, variables, hosts, instance_uuids,
                                request_spec, filter_properties):
        # Coefficients are 0 for hosts in the availability zone, 1 for others
        props = request_spec.get('instance_properties', {})
        availability_zone = props.get('availability_zone')

        coefficient_vectors = []
        for host in hosts:
            if availability_zone:
                context = filter_properties['context'].elevated()
                metadata = db.aggregate_metadata_get_by_host(context,
                                host.host, key='availability_zone')
                if 'availability_zone' in metadata:
                    if availability_zone in metadata['availability_zone']:
                        coefficient_vectors.append([0 for j in range(
                                                    self.num_instances)])
                    else:
                        coefficient_vectors.append([1 for j in range(
                                                    self.num_instances)])
                elif availability_zone == CONF.default_availability_zone:
                    coefficient_vectors.append([0 for j in range(
                                                self.num_instances)])
                else:
                    coefficient_vectors.append([1 for j in range(
                                                self.num_instances)])
            else:
                coefficient_vectors.append([0 for j in range(
                                                self.num_instances)])
        return coefficient_vectors

    def get_variable_vectors(self, variables, hosts, instance_uuids,
                            request_spec, filter_properties):
        # The variable_vectors[i,j] denotes the relationship between
        # host[i] and instance[j].
        variable_vectors = [[variables[i][j] for j in range(
                        self.num_instances)] for i in range(self.num_hosts)]
        return variable_vectors

    def get_operations(self, variables, hosts, instance_uuids, request_spec,
                        filter_properties):
        # Operations are '=='.
        operations = [(lambda x: x == 0) for i in range(self.num_hosts)]
        return operations

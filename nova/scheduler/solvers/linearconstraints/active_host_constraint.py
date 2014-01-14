# Copyright (c) 2012 OpenStack Foundation
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

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler import filters
from nova import servicegroup
from nova.scheduler.solvers import linearconstraints

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

class ActiveHostConstraint(linearconstraints.BaseLinearConstraint):
    """Constraint that only allows active hosts to be selected."""
    
    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) (constants)
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the (constants) is merged into left-hand-side,
    # thus the right-hand-side is 0.
    
    def __init__(self, variables, hosts, instance_uuids, request_spec, filter_properties):
        self.servicegroup_api = servicegroup.API()
        [self.num_hosts, self.num_instances] = self._get_host_instance_nums(hosts,instance_uuids,request_spec)
    
    def _get_host_instance_nums(self,hosts,instance_uuids,request_spec):
        """This method calculates number of hosts and instances"""
        num_hosts = len(hosts)
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
        return [num_hosts,num_instances]
    
    def get_coefficient_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        # Coefficients are 0 for active hosts and 1 otherwise
        coefficient_matrix = []
        for host in hosts:
            service = host.service
            if service['disabled'] or not self.servicegroup_api.service_is_up(service):
                coefficient_matrix.append([1 for j in range(self.num_instances)])
                LOG.debug(_("%s is not active") %host.host)
            else:
                coefficient_matrix.append([0 for j in range(self.num_instances)])
                LOG.debug(_("%s is ok") %host.host)
        return coefficient_matrix
    
    def get_variable_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        # The variable_matrix[i,j] denotes the relationship between host[i] and instance[j].
        variable_matrix = []
        variable_matrix = [[variables[i][j] for j in range(self.num_instances)] for i in range(self.num_hosts)]
        return variable_matrix
    
    def get_operations(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        # Operations are '=='.
        operations = [(lambda x: x==0) for i in range(self.num_hosts)]
        return operations
    

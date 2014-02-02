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

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler.solvers import linearconstraints

LOG = logging.getLogger(__name__)

class MaxInstancesPerHostConstraint(linearconstraints.BaseLinearConstraint):
    """Constraint that specifies the maximum number of instances that each host can launch."""
    
    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) (constants)
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the (constants) is merged into left-hand-side,
    # thus the right-hand-side is 0.
    
    hint_name = 'max_instances_per_host'
    
    def __init__(self, variables, hosts, instance_uuids, request_spec, filter_properties):
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
        # The coefficient for each variable is 1 and constant in each constraint is -(max_instances_per_host)
        scheduler_hints = filter_properties.get('scheduler_hints')
        max_instances_per_host = scheduler_hints.get(self.hint_name, 1)
        coefficient_matrix = [[1 for j in range(self.num_instances)] + [-max_instances_per_host] for i in range(self.num_hosts)]
        return coefficient_matrix
    
    def get_variable_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        # The variable_matrix[i,j] denotes the relationship between host[i] and instance[j].
        variable_matrix = []
        variable_matrix = [[variables[i][j] for j in range(self.num_instances)] + [1] for i in range(self.num_hosts)]
        return variable_matrix
    
    def get_operations(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        # Operations are '<='.
        operations = [(lambda x: x<=0) for i in range(self.num_hosts)]
        return operations
    

# Copyright (c) 2011 OpenStack Foundation
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

ram_allocation_ratio_opt = cfg.FloatOpt('ram_allocation_ratio',
        default=1.5,
        help='Virtual ram to physical ram allocation ratio which affects '
             'all ram filters. This configuration specifies a global ratio '
             'for RamFilter. For AggregateRamFilter, it will fall back to '
             'this configuration value if no per-aggregate setting found.')
CONF = cfg.CONF
CONF.register_opt(ram_allocation_ratio_opt)


class NumHostsPerInstanceConstraint(linearconstraints.BaseLinearConstraint):
    """Constraint that specifies the number of hosts each instance is assigned to."""
    
    hint_name = 'num_hosts_per_instance'
    
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
    
    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) (constants)
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the (constants) is merged into left-hand-side,
    # thus the right-hand-side is 0.
    
    def get_coefficient_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        """Giving 1 as coefficient and -(num_hosts_per_instance) as constant."""
        scheduler_hints = filter_properties.get('scheduler_hints')
        num_hosts_per_instance = scheduler_hints.get(self.hint_name, 1)
        coefficient_matrix = [[1 for i in range(self.num_hosts)] + [-num_hosts_per_instance] for j in range(self.num_instances)]
        return coefficient_matrix
    
    def get_variable_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        """rearrange variables."""
        variable_matrix = []
        variable_matrix = [[variables[i][j] for i in range(self.num_hosts)] + [1] for j in range(self.num_instances)]
        return variable_matrix
    
    def get_operations(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        """Giving operations as 'less than'."""
        operations = [(lambda x: x==0) for j in range(self.num_instances)]
        return operations
    

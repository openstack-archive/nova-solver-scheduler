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
CONF = cfg.CONF

ram_allocation_ratio_opt = cfg.FloatOpt('ram_allocation_ratio',
        default=1.0,
        help='Virtual ram to physical ram allocation ratio.')
CONF.register_opt(ram_allocation_ratio_opt)

disk_allocation_ratio_opt = cfg.FloatOpt("disk_allocation_ratio",
        default=1.0,
        help="Virtual disk to physical disk allocation ratio.")
CONF.register_opt(disk_allocation_ratio_opt)

class ResourceAllocationConstraint(linearconstraints.BaseLinearConstraint):
    """Base class of resource allocation constraints."""
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
    
class MaxDiskAllocationPerHostConstraint(ResourceAllocationConstraint):
    """Constraint of the maximum total disk demand acceptable on each host."""
    
    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) (constants)
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the (constants) is merged into left-hand-side,
    # thus the right-hand-side is 0.
    
    def get_coefficient_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        # Give demand as coefficient for each variable and -supply as constant in each constraint.
        demand = [self._get_required_disk_mb(filter_properties) for j in range(self.num_instances)]
        supply = [self._get_usable_disk_mb(hosts[i]) for i in range(self.num_hosts)]
        coefficient_matrix = [demand + [-supply[i]] for i in range(self.num_hosts)]
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
    
    def _get_usable_disk_mb(self, host_state):
        """This method returns the usable disk in mb for the given host.
         Takes into account the disk allocation ratio (virtual disk to physical disk allocation ratio)
        """
        free_disk_mb = host_state.free_disk_mb
        total_usable_disk_mb = host_state.total_usable_disk_gb * 1024
        disk_mb_limit = total_usable_disk_mb * CONF.disk_allocation_ratio
        used_disk_mb = total_usable_disk_mb - free_disk_mb
        usable_disk_mb = disk_mb_limit - used_disk_mb
        return usable_disk_mb
    
    def _get_required_disk_mb(self,filter_properties):
        """ This method returns the required disk in mb from
         the given filter_properties dictionary object
        """
        requested_disk_mb = 0
        instance_type = filter_properties.get('instance_type')
        if instance_type is not None:
            requested_disk_mb = 1024 * (instance_type.get('root_gb',0) +
                                 instance_type.get('ephemeral_gb',0))
        return requested_disk_mb

class MaxRamAllocationPerHostConstraint(ResourceAllocationConstraint):
    """Constraint of the total ram demand acceptable on each host."""
    
    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) (constants)
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the (constants) is merged into left-hand-side,
    # thus the right-hand-side is 0.
    
    def get_coefficient_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        # Give demand as coefficient for each variable and -supply as constant in each constraint.
        [num_hosts,num_instances] = self._get_host_instance_nums(hosts,instance_uuids,request_spec)
        demand = [self._get_required_memory_mb(filter_properties) for j in range(self.num_instances)]
        supply = [self._get_usable_memory_mb(hosts[i]) for i in range(self.num_hosts)]
        coefficient_matrix = [demand + [-supply[i]] for i in range(self.num_hosts)]
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
    
    def _get_usable_memory_mb(self,host_state):
        """This method returns the usable memory in mb for the given host.
         Takes into account the ram allocation ratio (Virtual ram to physical ram allocation ratio)
        """
        free_ram_mb = host_state.free_ram_mb
        total_usable_ram_mb = host_state.total_usable_ram_mb
        ram_allocation_ratio = CONF.ram_allocation_ratio
        memory_mb_limit = total_usable_ram_mb * ram_allocation_ratio
        used_ram_mb = total_usable_ram_mb - free_ram_mb
        usable_ram_mb = memory_mb_limit - used_ram_mb
        return usable_ram_mb
    
    def _get_required_memory_mb(self,filter_properties):
        """ This method returns the required memory in mb from
         the given filter_properties dictionary object
        """
        required_ram_mb = 0
        instance_type = filter_properties.get('instance_type')
        if instance_type is not None:
            required_ram_mb = instance_type.get('memory_mb',0)
        return required_ram_mb

class MaxVcpuAllocationPerHostConstraint(ResourceAllocationConstraint):
    """Constraint of the total vcpu demand acceptable on each host."""
    
    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) (constants)
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the (constants) is merged into left-hand-side,
    # thus the right-hand-side is 0.
    
    def get_coefficient_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        # Give demand as coefficient for each variable and -supply as constant in each constraint.
        [num_hosts,num_instances] = self._get_host_instance_nums(hosts,instance_uuids,request_spec)
        demand = [self._get_required_vcpus(filter_properties) for j in range(self.num_instances)]
        supply = [self._get_usable_vcpus(hosts[i]) for i in range(self.num_hosts)]
        coefficient_matrix = [demand + [-supply[i]] for i in range(self.num_hosts)]
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
    
    def _get_usable_vcpus(self,host_state):
        """This method returns the usable vcpus for the given host.
        """
        total_usable_vcpus = host_state.vcpus_total
        used_vcpus = host_state.vcpus_used
        usable_vcpus = total_usable_vcpus - used_vcpus
        return usable_vcpus
    
    def _get_required_vcpus(self,filter_properties):
        """ This method returns the required vcpus from
         the given filter_properties dictionary object
        """
        required_vcpus = 1
        instance_type = filter_properties.get('instance_type')
        if instance_type is not None:
            required_vcpus = instance_type.get('vcpus',1)
        return required_vcpus
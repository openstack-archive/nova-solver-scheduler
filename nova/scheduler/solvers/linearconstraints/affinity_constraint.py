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

from nova.compute import api as compute
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler.solvers import linearconstraints

LOG = logging.getLogger(__name__)

class AffinityConstraint(linearconstraints.BaseLinearConstraint):
    def __init__(self, variables, hosts, instance_uuids, request_spec, filter_properties):
        self.compute_api = compute.API()
        [self.num_hosts, self.num_instances] = self._get_host_instance_nums(hosts,instance_uuids,request_spec)
    def _get_host_instance_nums(self,hosts,instance_uuids,request_spec):
        """This method calculates number of hosts and instances"""
        num_hosts = len(hosts)
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
        return [num_hosts,num_instances]
    
class DifferentHostConstraint(AffinityConstraint):
    '''Force to select host which is different from a set of given instances'.'''
    
    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) constant_vector
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the constant_vector is merged into left-hand-side,
    # thus the right-hand-side is always 0.
    
    def get_coefficient_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        """Giving demand as coefficient and supply as constant."""
        context = filter_properties['context']
        scheduler_hints = filter_properties.get('scheduler_hints', {})
        affinity_uuids = scheduler_hints.get('different_host', [])
        if isinstance(affinity_uuids, basestring):
            affinity_uuids = [affinity_uuids]
        coefficient_matrix = []
        for host in hosts:
            if affinity_uuids:
                if self.compute_api.get_all(context,
                        {'host':host.host,
                        'uuid':affinity_uuids,
                        'deleted':False}):
                    coefficient_matrix.append([1 for j in range(self.num_instances)])
                    LOG.debug(_('found.'))
                else:
                    coefficient_matrix.append([0 for j in range(self.num_instances)])
            else:
                coefficient_matrix.append([0 for j in range(self.num_instances)])
        return coefficient_matrix
    
    def get_variable_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        """Organize the variables so that rows correspond to hosts, and columns correspond to instances."""
        variable_matrix = []
        variable_matrix = [[variables[i][j] for j in range(self.num_instances)] for i in range(self.num_hosts)]
        return variable_matrix
    
    def get_operations(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        """Giving operations as 'less than'."""
        operations = [(lambda x: x==0) for i in range(self.num_hosts)]
        return operations
    
class SameHostConstraint(AffinityConstraint):
    '''Force to select host which is different from a set of given instances'.'''
    
    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) constant_vector
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the constant_vector is merged into left-hand-side,
    # thus the right-hand-side is always 0.
    
    def get_coefficient_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        """Giving demand as coefficient and supply as constant."""
        context = filter_properties['context']
        scheduler_hints = filter_properties.get('scheduler_hints', {})
        affinity_uuids = scheduler_hints.get('different_host', [])
        if isinstance(affinity_uuids, basestring):
            affinity_uuids = [affinity_uuids]
        coefficient_matrix = []
        for host in hosts:
            if affinity_uuids:
                if self.compute_api.get_all(context,
                        {'host':host.host,
                        'uuid':affinity_uuids,
                        'deleted':False}):
                    coefficient_matrix.append([0 for j in range(self.num_instances)])
                    LOG.debug(_('found.'))
                else:
                    coefficient_matrix.append([1 for j in range(self.num_instances)])
            else: coefficient_matrix.append([0 for j in range(self.num_instances)])
        return coefficient_matrix
    
    def get_variable_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        """Organize the variables so that rows correspond to hosts, and columns correspond to instances."""
        variable_matrix = []
        variable_matrix = [[variables[i][j] for j in range(self.num_instances)] for i in range(self.num_hosts)]
        return variable_matrix
    
    def get_operations(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        """Giving operations as 'less than'."""
        operations = [(lambda x: x==0) for i in range(self.num_hosts)]
        return operations
    
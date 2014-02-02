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

"""
Linear constraints for scheduler linear constraint solvers
"""


from nova import loadables

class BaseLinearConstraint(object):
    """Base class for linear constraint"""
    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) (constants)
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the (constants) is merged into left-hand-side,
    # thus the right-hand-side is 0.
    def __init__(self, variables, hosts, instance_uuids, request_spec, filter_properties):
        pass
    def get_coefficient_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        """Retruns constraint matrix."""
        raise NotImplementedError()
    def get_variable_matrix(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        """Returns variable matrix."""
        raise NotImplementedError()
    def get_operations(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        """Returns operations."""
        raise NotImplementedError()
    
class LinearConstraintHandler(loadables.BaseLoader):
    def __init__(self):
        super(LinearConstraintHandler, self).__init__(BaseLinearConstraint)
    
def all_linear_constraints():
    """Return a list of lineear constraint classes found in this directory.

    This method is used as the default for available linear constraints for scheduler
    and should return a list of all linearconstraint classes available.
    """
    
    return LinearConstraintHandler().get_all_classes()
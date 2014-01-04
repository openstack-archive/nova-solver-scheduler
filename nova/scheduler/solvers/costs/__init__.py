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

"""
Costs for scheduler constraint solvers
"""

from nova import filters
from nova import loadables

class BaseCost(object):
    """Base class for cost."""
    def get_cost_matrix(self,hosts,instance_uuids,request_spec,filter_properties):
        """Return the cost matrix. Implement this in a subclass."""
        raise NotImplementedError()
    def normalize_cost_matrix(self,cost_matrix,lower_bound=0.0,upper_bound=1.0):
        """Normalize the cost matrix, by default using linear scaling to [0,1]."""
        if (lower_bound > upper_bound):
            return None
        cost_array = []
        normalized_cost_matrix = list(cost_matrix)
        for i in range(len(cost_matrix)):
            for j in range(len(cost_matrix[i])):
                cost_array.append(cost_matrix[i][j])
        max_cost = max(cost_array)
        min_cost = min(cost_array)
        for i in range(len(normalized_cost_matrix)):
            for j in range(len(normalized_cost_matrix[i])):
                if max_cost == min_cost:
                    normalized_cost_matrix[i][j] = (upper_bound + lower_bound) / 2
                else:
                    normalized_cost_matrix[i][j] = lower_bound + (cost_matrix[i][j] - min_cost) * (upper_bound - lower_bound) / (max_cost - min_cost)
        return normalized_cost_matrix

class CostHandler(loadables.BaseLoader):
    def __init__(self):
        super(CostHandler, self).__init__(BaseCost)
    
def all_costs():
    """Return a list of cost classes found in this directory.

    This method is used as the default for available costs for scheduler
    and should return a list of all cost classes available.
    """
    
    return CostHandler().get_all_classes()
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

"""Ram cost."""

from oslo.config import cfg

from nova import exception
from nova.openstack.common import log as logging
from nova.scheduler.solvers import costs as solvercosts

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


ram_weight_opts = [
        cfg.FloatOpt('ram_cost_optimization_multiplier',
                     default=1.0,
                     help='Multiplier used for ram optimization cost metric. This '
                          'solver uses a LP minimization problem. So a negative '
                          'number would mean a cost maximization problem.'),
]
CONF.register_opts(ram_weight_opts)

class RamCost(solvercosts.BaseCost):
    """Calculation of ram cost:
    host.free_ram_mb*CONF.ram_cost_optimization_multiplier .
    """
    def get_cost_name(self):
        return self.__name__
    
    def get_cost_matrix(self,hosts,instance_uuids,request_spec,filter_properties):
        num_hosts = len(hosts)
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
        
        costs = [[hosts[i].free_ram_mb*CONF.ram_cost_optimization_multiplier for j in range(num_instances)] for i in range(num_hosts)]
        
        return costs
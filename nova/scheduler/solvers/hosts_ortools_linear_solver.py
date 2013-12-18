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

# add pluggable constraints

from oslo.config import cfg

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.openstack.common import importutils
from nova.scheduler import solvers as novasolvers
from nova.scheduler.solvers import costs
from nova.scheduler.solvers import linearconstraints
#from pulp import *
from linear_solver import pywraplp

LOG = logging.getLogger(__name__)

scheduler_solver_costs_opt = cfg.ListOpt('scheduler_solver_costs',
        default=[
                'nova.scheduler.solvers.costs.ram_cost.RamCost'
                ],
        help='Which cost matrices to use in the scheduler solver')

scheduler_solver_cost_weights_opt = cfg.DictOpt('scheduler_solver_cost_weights',
        default={'RamCost':0.0},
        help='assign the weights for each cost')

scheduler_solver_constraints_opt = cfg.ListOpt('scheduler_solver_constraints',
        default=[],
        help='which constraints to be used in scheduler solver')

CONF = cfg.CONF
CONF.register_opt(scheduler_solver_costs_opt)
CONF.register_opt(scheduler_solver_cost_weights_opt)
CONF.register_opt(scheduler_solver_constraints_opt)


class HostsOrtoolsLinearSolver(novasolvers.BaseHostSolver):
    """ A LP based constraint solver implemented using Google or-tools modeler """
    def __init__(self):
        self.cost_classes = []
        self.cost_weights = {}
        self.constraint_classes = []
        cost_handler = costs.CostHandler()
        all_cost_classes = cost_handler.get_all_classes()
        for costName in CONF.scheduler_solver_costs:
            for costCls in all_cost_classes:
                if costCls.__name__ == costName:
                    self.cost_classes.append(costCls)
        constraint_handler = linearconstraints.LinearConstraintHandler()
        all_constraint_classes = constraint_handler.get_all_classes()
        for constraintName in CONF.scheduler_solver_constraints:
            for constraintCls in all_constraint_classes:
                if constraintCls.__name__ == constraintName:
                    self.constraint_classes.append(constraintCls)
        self.cost_weights = CONF.scheduler_solver_cost_weights
        
    def host_solve(self, hosts, instance_uuids, request_spec, filter_properties):
        """ This method returns a list of tuples - (host, instance_uuid) that are returned by the solver
            Here the assumption is that all instance_uuids have the same requirement as specified in
            filter_properties
        """
        
        host_instance_tuples_list = []
        #Implement the solver logic here
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
            #Setting a unset uuid string for each instance
            instance_uuids = ['unset_uuid'+str(i) for i in xrange(num_instances)]
        
        num_hosts = len(hosts)
        
        #A list of HostsIds
        LOG.debug(_("All Hosts: %s") % [h.host for h in hosts])
        
        for host in hosts:
            LOG.debug(_("Host state: %s") % host)
        
        solver = pywraplp.Solver('Scheduler', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)
        
        # adjacency matrix specifying whether an instance is assigned to a host (variables to be solved)
        variables = [[solver.IntVar(0, 1, 'variables[%i,%i]' % (i, j)) for j in range(num_instances)] for i in range(num_hosts)]
        
        # create cost and constraint instances from their classes
        self.cost_objects = [cost() for cost in self.cost_classes]
        self.constraint_objects = [constraint(variables,hosts,instance_uuids,request_spec,filter_properties) for constraint in self.constraint_classes]
        
        #costs = [  # Instances
        #          # 1 2 3 4 5
        #          [2, 4, 5, 2, 1],  # A   Hosts
        #          [3, 1, 3, 2, 3]  # B
        #          ]
        
        #Creates a list of costs of each Host-Instance assignment
        costs = [[0 for j in range(num_instances)] for i in range(num_hosts)]
        
        for costObject in self.cost_objects:
            cost = costObject.get_cost_matrix(hosts, instance_uuids, request_spec, filter_properties)
            cost = costObject.normalize_cost_matrix(cost,0.0,1.0)
            weight = float(self.cost_weights[costObject.__class__.__name__])
            LOG.debug(_('The cost matrix is {}'.format(cost)))
            LOG.debug(_('Weight equals {}'.format(weight)))
            costs = [[costs[i][j] + weight * cost[i][j] for j in range(num_instances)] for i in range(num_hosts)]
        
        # objective function
        objfunc = solver.Sum([costs[i][j]*variables[i][j] for i in range(num_hosts) for j in range(num_instances)])
        
        # get linear constraints
        for constraintObject in self.constraint_objects:
            coefficient_matrix = constraintObject.get_coefficient_matrix(variables,hosts,instance_uuids,request_spec,filter_properties)
            variable_matrix = constraintObject.get_variable_matrix(variables,hosts,instance_uuids,request_spec,filter_properties)
            operations = constraintObject.get_operations(variables,hosts,instance_uuids,request_spec,filter_properties)
            for i in range(len(operations)):
                operation = operations[i]
                len_vector = len(variable_matrix[i])
                solver.Add(operation(solver.Sum([coefficient_matrix[i][j] * variable_matrix[i][j] for j in range(len_vector)])))
        
        objective = solver.Minimize(objfunc)
        
        solver.Solve()
        
        for i in range(num_hosts):
            for j in range(num_instances):
                if int(variables[i][j].SolutionValue()) == 1:
                    host_instance_tuples_list.append((hosts[i],instance_uuids[j]))
        
        return host_instance_tuples_list

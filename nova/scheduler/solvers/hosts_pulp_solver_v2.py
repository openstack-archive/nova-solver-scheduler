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


"""
Scheduler linear constraint solver using PULP moduler.
The cost functions and linear constraints are pluggable and
configurable by user.
"""

from oslo.config import cfg

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.openstack.common import importutils
from nova.scheduler import solvers as novasolvers
from nova.scheduler.solvers import costs
from nova.scheduler.solvers import linearconstraints

from pulp import *

LOG = logging.getLogger(__name__)

scheduler_solver_costs_opt = cfg.ListOpt(
        'scheduler_solver_costs',
        default=['nova.scheduler.solvers.costs.ram_cost.RamCost'],
        help='Which cost matrices to use in the scheduler solver.')

scheduler_solver_cost_weights_opt = cfg.DictOpt(
        'scheduler_solver_cost_weights',
        default={'RamCost':1.0},
        help='Assign weight for each cost')

scheduler_solver_constraints_opt = cfg.ListOpt(
        'scheduler_solver_constraints',
        default=[],
        help='Which constraints to use in scheduler solver')

CONF = cfg.CONF
CONF.register_opt(scheduler_solver_costs_opt)
CONF.register_opt(scheduler_solver_cost_weights_opt)
CONF.register_opt(scheduler_solver_constraints_opt)


class HostsPulpSolver(novasolvers.BaseHostSolver):
    """ A LP based constraint solver implemented using PULP modeler """
    def __init__(self):
        self.cost_classes = []
        self.cost_weights = {}
        self.constraint_classes = []
        
        # Get cost classes.
        cost_handler = costs.CostHandler()
        all_cost_classes = cost_handler.get_all_classes()
        for costName in CONF.scheduler_solver_costs:
            for costCls in all_cost_classes:
                if costCls.__name__ == costName:
                    self.cost_classes.append(costCls)
        # Get constraint classes.
        constraint_handler = linearconstraints.LinearConstraintHandler()
        all_constraint_classes = constraint_handler.get_all_classes()
        for constraintName in CONF.scheduler_solver_constraints:
            for constraintCls in all_constraint_classes:
                if constraintCls.__name__ == constraintName:
                    self.constraint_classes.append(constraintCls)
        # Get cost weights.
        self.cost_weights = CONF.scheduler_solver_cost_weights
        
    def host_solve(self, hosts, instance_uuids, request_spec, filter_properties):
        """ This method returns a list of tuples - (host, instance_uuid) that are returned by the solver
            Here the assumption is that all instance_uuids have the same requirement as specified in
            filter_properties
        """
        host_instance_tuples_list = []
        
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
            #Setting a unset uuid string for each instance.
            instance_uuids = ['unset_uuid'+str(i) for i in xrange(num_instances)]
        num_hosts = len(hosts)
        
        # Create dictionaries mapping host/instance IDs to hosts/instances.
        Hosts = ['Host' + str(i) for i in range(num_hosts)]
        HostIdDict  = dict(zip(Hosts,hosts))
        Instances = ['Instance' + str(i) for i in range(num_instances)]
        InstanceIdDict = dict(zip(Instances, instance_uuids))
        # Create a list of tuples containing all the possible HostInstanceTuples.
        AllHostInstanceTuples = [(i, j) for i in Hosts for j in Instances]
        
        LOG.debug(_("All Hosts: %s") % [h.host for h in hosts])
        for host in hosts:
            LOG.debug(_("Host state: %s") % host)
        
        # Create the 'prob' variable to contain the problem data.
        prob = LpProblem("Host Instance Scheduler Problem", LpMinimize)
        
        # Create the 'variables' matrix to contain the referenced variables.
        variables = [[LpVariable("IA"+"_Host"+str(i)+"_Instance"+str(j), 0, 1, LpInteger) for j in range(num_instances)] for i in range(num_hosts)]
        
        # Get costs and constraints and formulate the linear problem.
        self.cost_objects = [cost() for cost in self.cost_classes]
        self.constraint_objects = [constraint(variables,hosts,instance_uuids,request_spec,filter_properties) for constraint in self.constraint_classes]
        
        costs = [[0 for j in range(num_instances)] for i in range(num_hosts)]
        for costObject in self.cost_objects:
            cost = costObject.get_cost_matrix(hosts, instance_uuids, request_spec, filter_properties)
            cost = costObject.normalize_cost_matrix(cost,0.0,1.0)
            weight = float(self.cost_weights[costObject.__class__.__name__])
            LOG.debug(_('The cost matrix is {}'.format(cost)))
            LOG.debug(_('Weight equals {}'.format(weight)))
            costs = [[costs[i][j] + weight * cost[i][j] for j in range(num_instances)] for i in range(num_hosts)]
        prob += lpSum([costs[i][j] * variables[i][j] for i in range(num_hosts) for j in range(num_instances)]), "Sum_of_Host_Instance_Scheduling_Costs"
        
        for constraintObject in self.constraint_objects:
            coefficient_matrix = constraintObject.get_coefficient_matrix(variables,hosts,instance_uuids,request_spec,filter_properties)
            variable_matrix = constraintObject.get_variable_matrix(variables,hosts,instance_uuids,request_spec,filter_properties)
            operations = constraintObject.get_operations(variables,hosts,instance_uuids,request_spec,filter_properties)
            for i in range(len(operations)):
                operation = operations[i]
                len_vector = len(variable_matrix[i])
                prob += operation(lpSum([coefficient_matrix[i][j] * variable_matrix[i][j] for j in range(len_vector)])),\
                        "Costraint_Name_%s" % constraintObject.__class__.__name__ + "_By_Host_%s" % i
        
        # Write problem data to an .lp file.
        # prob.writeLP("HostsPulpSolver.lp")
        
        # The problem is solved using PULP's choice of Solver.
        prob.solve()
        
        # Create host-instance tuples from the solutions.
        if LpStatus[prob.status] == 'Optimal':
            for v in prob.variables():
                if v.name.startswith('IA'):
                    (hostId, instanceId) = v.name.lstrip('IA').lstrip('_').split('_')
                    if v.varValue == 1.0:
                        host_instance_tuples_list.append((HostIdDict[hostId], InstanceIdDict[instanceId]))
        
        return host_instance_tuples_list

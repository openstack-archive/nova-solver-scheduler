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
Scheduler linear constraint solver using or-tools moduler.
The cost functions and linear constraints are pluggable and
configurable by user.
"""

from oslo.config import cfg

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.openstack.common import importutils
from nova.scheduler import solvers as scheduler_solver
from nova.scheduler.solvers import costs
from nova.scheduler.solvers import linearconstraints

from linear_solver import pywraplp

LOG = logging.getLogger(__name__)


class HostsOrtoolsLinearSolver(scheduler_solver.BaseHostSolver):
    """ A LP based constraint solver implemented using Google or-tools modeler """
    def __init__(self):
        self.cost_classes = self._get_cost_classes()
        self.constraint_classes = self._get_constraint_classes()
        self.cost_weights = self._get_cost_weights()
        
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
            #Setting a unset uuid string for each instance
            instance_uuids = ['unset_uuid'+str(i) for i in xrange(num_instances)]
        num_hosts = len(hosts)
        
        # Print a list of hosts and their states
        LOG.debug(_("All Hosts: %s") % [h.host for h in hosts])
        for host in hosts:
            LOG.debug(_("Host state: %s") % host)
        
        # Create the linear solver.
        solver = pywraplp.Solver('Scheduler', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)
        
        # Create the 'variables' matrix to contain the referenced variables.
        variables = [[solver.IntVar(0, 1, 'variables[%i,%i]' % (i, j)) for j in range(num_instances)] for i in range(num_hosts)]
        
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
        objfunc = solver.Sum([costs[i][j]*variables[i][j] for i in range(num_hosts) for j in range(num_instances)])
        
        for constraintObject in self.constraint_objects:
            coefficient_matrix = constraintObject.get_coefficient_matrix(variables,hosts,instance_uuids,request_spec,filter_properties)
            variable_matrix = constraintObject.get_variable_matrix(variables,hosts,instance_uuids,request_spec,filter_properties)
            operations = constraintObject.get_operations(variables,hosts,instance_uuids,request_spec,filter_properties)
            for i in range(len(operations)):
                operation = operations[i]
                len_vector = len(variable_matrix[i])
                solver.Add(operation(solver.Sum([coefficient_matrix[i][j] * variable_matrix[i][j] for j in range(len_vector)])))
        
        # Solve the linear problem.
        objective = solver.Minimize(objfunc)
        solver.Solve()
        
        # create host-instance tuples from the solutions.
        for i in range(num_hosts):
            for j in range(num_instances):
                if int(variables[i][j].SolutionValue()) == 1:
                    host_instance_tuples_list.append((hosts[i],instance_uuids[j]))
        
        return host_instance_tuples_list

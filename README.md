Openstack Nova Solver Scheduler
===============================

Solver Scheduler is an Openstack Nova Scheduler driver that provides a smarter, complex constraints optimization based resource scheduling in Nova.  It is a pluggable scheduler driver, that can leverage existing complex constraint solvers available in open source such as PULP, CVXOPT, Google OR-TOOLS, etc. It can be easily extended to add complex constraint models for various use cases, written using any of the available open source constraint solving frameworks. 

Getting Started
===============
The project code has to be patched onto an existing installation of Openstack Nova, as it is a pluggable Nova scheduler driver.

Key modules
===========
* nova/scheduler/solver_scheduler.py    -  The new scheduler driver module
* nova/scheduler/host_manager.py   - A patched version of host_manager module from the master Nova project, with a new method.

The code includes a reference implementation of a solver that models the scheduling problem as a Linear Programming model, written using the PULP LP modeling language. It uses a PULP_CBC_CMD, which is a packaged constraint solver, included in the coinor-pulp python package.  

*  nova/scheduler/solvers/hosts_pulp_solver.py

There are two examples of pluggable solvers using coinor-pulp or or-tools package, where costs functions and linear constraints can be plugged into the solver.

*  nova/scheduler/solvers/hosts_pulp_solver_v2.py
*  nova/scheduler/solvers/hosts_ortools_linear_solver.py

Additional modules
==================

The cost functions pluggable to solver:

* nova/scheduler/solvers/costs/ram_cost.py      - Cost function that can help to balance (or stack) ram usage of all hosts
    - Note: requires scheduler hint: ram_cost_optimization_multiplier=<the multiplier number>
* nova/scheduler/solvers/costs/ip_distance_cost.py      - Cost function that evaluates the distance between a colume and a vm using ip address
    - Note: requires scheuler hint: ip_distance_cost_volume_id=<volume id>

The linear constraints that are pluggable to solver:

* nova/scheduler/solvers/linearconstraints/affinity_constraint.py       - Constraint that forces instances to be placed away from a set of instances, or at the same host as a set of instances
    - Note: requires scheduler hint: different_host=<list of instance uuids> or same_host=<list of instance uuids>
* nova/scheduler/solvers/linearconstraints/num_hosts_per_instance_constraint.py     - Constraint that forces each instance to be placed in exactly certain number (normally 1) of hosts, this is necessary for getting correct solution from solver
* nova/scheduler/solvers/linearconstraints/resource_allocation_constraint.py        - Constraints that ensure host resources (ram, disk, vcpu, etc.) not to be over allocated


Requirements:
=============
* coinor-pulp>=1.0.4
* or-tools>=1.0.2902
  
Configurations:
==============

The following additional configuration options have to be added to nova.conf file:

* This is for changing the scheduler driver used by Nova.

scheduler_driver = nova.scheduler.solver_scheduler.ConstraintSolverScheduler

* This is for changing the solver module to be used by the above solver scheduler. If you implement your own constraints modules with constraints for your use cases, update this option.

scheduler_host_solver = nova.scheduler.solvers.hosts_pulp_solver.HostsPulpSolver


The following configuration options need to be added to nova.conf if using these solvers: hosts_pulp_solver_v2.py, hosts_ortools_linear_solver.py

* This is for setting the cost functions that are used in the solver

scheduler_solver_costs = RamCost, IpDistanceCost

* This is for setting the weight of each cost

scheduler_solver_cost_weights = RamCost:0.7, IpDistanceCost:0.2

* This is for setting the constraints used in the solver

scheduler_solver_constraints = NumHostsPerInstanceConstraint, MaxDiskAllocationPerHostConstraint, MaxRamAllocationPerHostConstraint

Openstack Nova Solver Scheduler
===============================

Solver Scheduler is an Openstack Nova Scheduler driver that provides a smarter, complex constraints optimization based resource scheduling in Nova.  It is a pluggable scheduler driver, that can leverage existing complex constraint solvers available in open source such as PULP, CVXOPT, Google OR-TOOLS, etc. It can be easily extended to add complex constraint models for various use cases, written using any of the available open source constraint solving frameworks. 

GETTING STARTED
===============
The project code has to be patched onto an existing installation of Openstack Nova, as it is a pluggable Nova scheduler driver.

Key modules:
===========
* nova/scheduler/solver_scheduler.py    -  The new scheduler driver module
* nova/scheduler/host_manager.py   - A patched version of host_manager module from the master Nova project, with a new method.

The code includes a reference implementation of a solver that models the scheduling problem as a Linear Programming model, written using the PULP LP modeling language. It uses a PULP_CBC_CMD, which is a packaged constraint solver, included in the coinor-pulp python package.  

*  nova/scheduler/solvers/hosts_pulp_solver.py


Requirements:
=============
* coinor-pulp>=1.0.4
  
Configurations:
==============

* nova.conf:

The following additional configuration options have to be added to nova.conf file:

# This is for changing the scheduler driver used by Nova
scheduler_driver = nova.scheduler.solver_scheduler.ConstraintSolverScheduler

# This is for changing the solver module to be used by the above solver scheduler
# If you implement your own constraints modules with constraints for your use cases, update this option
scheduler_host_solver = nova.scheduler.solvers.hosts_pulp_solver.HostsPulpSolver



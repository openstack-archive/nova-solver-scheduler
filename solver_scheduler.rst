Solver Scheduler
================

The **Solver Scheduler** provides an extensible mechanism for making smarter,
complex constraints optimization based resource scheduling in Nova. This
driver supports pluggable Solvers, that can leverage existing complex
constraint solving frameworks, available in open source such as PULP_, CVXOPT_,
`Google OR-TOOLS`_, etc. This Scheduler is currently supported to work with
Compute Nodes in Nova.

.. _PULP: https://projects.coin-or.org/PuLP

.. _CVXOPT: http://cvxopt.org/

.. _`Google OR-TOOLS`: https://code.google.com/p/or-tools/

The Nova compute resource placement can be described as a problem of placing a
set of VMs on a set of physical hosts, where each VM has a set of resource
requirements that have to be satisfied by a host with available resource
capacity. In addition to the constraints, we optimize the solution for some
cost metrics, so that the net cost of placing all VMs to certain hosts is
minimized.

A pluggable Solver used by the Solver Scheduler driver models the Nova compute
placement request as a constraint optimization problem using a set of
constraints derived from the placement request specification and a net cost
value to optimize. A Solver implementation should model the constraints and
costs and feed it to a constraint problem specification, which
is eventually solved by using any external solvers such as the COIN-OR_ CLP_,
CBC_, GLPK_, and so on.

.. _COIN-OR: http://en.wikipedia.org/wiki/COIN-OR

.. _CLP: http://en.wikipedia.org/wiki/COIN-OR#CLP

.. _CBC: http://en.wikipedia.org/wiki/COIN-OR#CBC

.. _GLPK: http://en.wikipedia.org/wiki/GNU_Linear_Programming_Kit

The Nova compute resource placement optimization problem when subject to a set
of linear constraints, can be formulated and solved as a `linear programming`_
problem. A **linear programming (LP)** problem involves maximizing or
minimizing a linear function subject to linear constraints.

.. _linear programming: http://en.wikipedia.org/wiki/Linear_programming

Solvers
-------

All Solver implementations will be in the module
(:mod:`nova_solverscheduler.scheduler.solvers`). A solver implementation should be a
subclass of ``solvers.BaseHostSolver`` and they implement the ``host_solve``
method. This method returns a list of host-instance tuples after solving
the constraints optimization problem.

A Reference Solver Implementation
---------------------------------
|HostsPulpSolver| is a reference solver implementation that models the Nova
scheduling problem as a linear programming (LP) problem using the PULP_
modeling framework. This example implementation is a working solver that
includes the required disk and memory as constraints, and uses the free ram
as a cost metric to maximize (for spreading hosts), or minimize (for stacking)
for the LP problem.

An example LP problem formulation is provided below to describe how this
example solver models the problem in LP.

Consider there are 2 hosts `Host_1` and `Host_2`, with available resources
described as a tuple (usable_disk_mb, usable_memory_mb, free_ram_mb):

* `Host_1`: (2048, 2048, 2048)

* `Host_2`: (4096, 1536, 1536)

There are two VM requests with the following disk and memory requirements:

* `VM_1`: (1024, 512)

* `VM_2`: (1024, 512)

To formulate this problem as a LP problem, we use the variables: `X11`, `X12`,
`X21`, `X22`. Here, a variable `Xij` takes the value `1` if `VM_i` is placed on
`Host_j`, `0` otherwise.

If the problem objective is to minimize the cost metric of free_ram_mb, the
mathematical LP formulation of this example is as follows:

::

    Minimize (2048*X11 + 2048*X21 + 1536*X12 + 1536*X22)

     subject to constraints:

     X11*1024 + X21*1024 <= 2048 (disk maximum supply for Host_1)
     X11*512  + X21*512  <= 2048 (memory maximum supply for Host_1)
     X12*1024 + X22*1024 <= 4096 (disk maximum supply for Host_2)
     X12*512  + X22*512  <= 1536 (memory maximum supply for Host_2)
     X11*1024 + X12*1024 >= 1024 (disk minimum demand for VM_1)
     X11*512  + X12*512  >= 512  (memory minimum demand for VM_1)
     X21*1024 + X22*1024 >= 1024 (disk minimum demand for VM_2)
     X21*512  + X22*512  >= 512  (memory minimum demand for VM_2)
     X11      + X12      == 1    (VM_1 can run in only 1 Host)
     X21      + X22      == 1    (VM_2 can run in only 1 Host)

`X11` = 0, `X12` = 1, `X21` = 0, and `X22` = 1 happens to be the optimal
solution, implying, both `VM_1` and `VM_2` will be hosted in `Host_2`.

|HostsPulpSolver| models such LP problems using the PULP_ LP modeler written in
Python. This problem is solved for an optimal solution using an external
solver supported by PULP such as CLP_, CBC_, GLPK_, etc.  By default, PULP_
uses the CBC_ solver, which is packaged with the `coinor.pulp`_ distribution.

.. _`coinor.pulp`: https://pypi.org/project/coinor.pulp

Additional Solver implementations are planned in the roadmap, that support
pluggable constraints and costs.


Configuration
-------------

To use Solver Scheduler, the nova.conf should contain the following settings
under the ``[solver_scheduler]`` namespace:

`The Solver Scheduler driver to use (required):`

``scheduler_driver=nova_solverscheduler.scheduler.solver_scheduler.ConstraintSolverScheduler``

`The Solver implementation to use:`

``scheduler_host_solver=nova_solverscheduler.scheduler.solvers.hosts_pulp_solver.HostsPulpSolver``

When using the default provided Solver implementation |HostsPulpSolver|, the
following default values of these settings can be modified:

These are under the ``[DEFAULT]`` namespace, as they are also being used by
the Filter Scheduler as well.

`The ram weight multiplier. A negative value indicates stacking as opposed
to spreading:`

``ram_weight_multiplier=1.0``

`Virtual disk to physical disk allocation ratio:`

``disk_allocation_ratio=1.0``

`Virtual ram to physical ram allocation ratio:`

``ram_allocation_ratio=1.5``

.. |HostsPulpSolver| replace:: :class:`HostsPulpSolver <nova_solverscheduler.scheduler.solvers.hosts_pulp_solver.HostsPulpSolver>`

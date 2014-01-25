Openstack Nova Solver Scheduler
===============================

Solver Scheduler is an Openstack Nova Scheduler driver that provides a smarter, complex constraints optimization based resource scheduling in Nova.  It is a pluggable scheduler driver, that can leverage existing complex constraint solvers available in open source such as PULP, CVXOPT, Google OR-TOOLS, etc. It can be easily extended to add complex constraint models for various use cases, written using any of the available open source constraint solving frameworks. 

Getting Started
---------------
The project code has to be patched onto an existing installation of Openstack Nova, as it is a pluggable Nova scheduler driver.

Key modules
-----------

* The new scheduler driver module:

    nova/scheduler/solver_scheduler.py

* A patched version of host_manager module from the master Nova project, with a new method:

    nova/scheduler/host_manager.py

* The code includes a reference implementation of a solver that models the scheduling problem as a Linear Programming model, written using the PULP LP modeling language. It uses a PULP_CBC_CMD, which is a packaged constraint solver, included in the coinor-pulp python package.

    nova/scheduler/solvers/hosts_pulp_solver.py

* There are two examples of pluggable solvers using coinor-pulp or or-tools package, where costs functions and linear constraints can be plugged into the solver.

    nova/scheduler/solvers/hosts_pulp_solver_v2.py  
    nova/scheduler/solvers/hosts_ortools_linear_solver.py

Additional modules
------------------

* The cost functions pluggable to solver:

    nova/scheduler/solvers/costs/ram_cost.py  
    nova/scheduler/solvers/costs/ip_distance_cost.py  

* The linear constraints that are pluggable to solver:

    nova/scheduler/solvers/linearconstraints/active_host_constraint.py  
    nova/scheduler/solvers/linearconstraints/affinity_constraint.py  
    nova/scheduler/solvers/linearconstraints/num_hosts_per_instance_constraint.py  
    nova/scheduler/solvers/linearconstraints/max_instances_per_host_constraint.py  
    nova/scheduler/solvers/linearconstraints/resource_allocation_constraint.py  

Requirements
------------

* coinor.pulp>=1.0.4
* or-tools>=1.0.2902 (Alternative. There is a known issue with or-tools package. See below.)

Known Issues
------------

* In some cases, the installation of or-tools package may cause unexpected crash of multiple OpenStack services due to a dependency problem. There has not been report of this issue for usage in Devstack environment.

Installing Solver Scheduler
---------------------------

The Solver Scheduler Manger will allow you to manage the solver scheduler in your openstack installation.

* **Note:**  
    - This is an **alpha** version, which was tested on **Ubuntu 12.04** and **OpenStack Havana** only.
    - It is recommended that a backup of the following files be kept before using this manager:  
        /etc/nova/nova.conf  
        nova/scheduler/host_manager.py  

To install the manager, run:  
```curl https://raw.github.com/CiscoSystems/nova-solver-scheduler/master/install_manager | sudo bash```

To install solver scheduler with this manager, use the following command as root:  
```
solver-scheduler install
```
To manage the solver scheduler, use one of the following commands as root:  
```
solver-scheduler activate
solver-scheduler deactivate
solver-scheduler remove
solver-scheduler update
solver-scheduler help
```

Configurations
--------------

* This is a configuration sample for the solver-scheduler. Please add these options to nova.conf.
* Note:
    - Instead of being added, the following existing options should be updated with new values: scheduler_driver
    - The module 'nova.scheduler.solvers.hosts_pulp_solver' is self-inclusive and non-pluggable for costs and constraints. Therefore, if the option 'scheduler_host_solver' is set to use this module, there is no need for additional costs/constraints configurations.
    - Please refer to the 'Configuration Details' section below for proper configuration of costs and constraints.

```
#
# Solver Scheduler Options
#

# Default driver to use for the scheduler
scheduler_driver = nova.scheduler.solver_scheduler.ConstraintSolverScheduler

# Default solver to use for the solver scheduler
scheduler_host_solver = nova.scheduler.solvers.hosts_pulp_solver_v2.HostsPulpSolver

# Cost functions to use in the linear solver
scheduler_solver_costs = RamCost, IpDistanceCost

# Weight of each cost (every cost function used should be given a weight.)
scheduler_solver_cost_weights = RamCost:0.25, IpDistanceCost:0.75

# Constraints used in the solver
scheduler_solver_constraints = ActiveHostConstraint, NumHostsPerInstanceConstraint, MaxDiskAllocationPerHostConstraint, MaxRamAllocationPerHostConstraint

# Way of ram usage
# set negative for balancing
# set positive for stacking
ram_cost_optimization_multiplier = -1

# Virtual-to-physical disk allocation ratio
linearconstraint_disk_allocation_ratio = 1.0

# Virtual-to-physical ram allocation ratio
linearconstraint_ram_allocation_ratio = 1.0
```

Configuration Details
---------------------

* Available costs  

    - **RamCost**  
        Help to balance (or stack) ram usage of hosts.  
        The following option should be set in configuration when using this cost:  
        ```ram_cost_optimization_multiplier = <a real number>```  
        Set the multiplier to negative number for balanced ram usage,  
        set the multiplier to positive number for stacked ram usage.  
    
    - **IpDistanceCost**  
        Help to place instances close to a set of volumes.  
        The distance between instances and volumes are evaluated by using ip address.  
        The following scheuler hint is expected when using this cost:  
        ```ip_distance_cost_volume_id_list = <a list of volume ids>```  

* Available linear constraints  

    - **ActiveHostConstraint**  
        Only enabled and operational hosts are allowed in solution.  
        Normally this constraint should always be enabled.  
    
    - **AffinityConstraint**  
        Force instances to be placed at either different or same hosts as a given set of instances.  
        The following scheduler hint is expected when using this constraint:  
        ```different_host = <a list of instance uuids>``` or ```same_host= <a list of instance uuids>```  
    
    - **NumHostsPerInstanceConstraint**  
        The purpose of this constraint is to avoid trivial solution (i.e. instances placed nowhere).  
        Normally this constraint should always be enabled.  
    
    - **MaxInstancesPerHostConstraint**  
        Specify the maximum number of instances placed in each host in each scheduling process.  
        The following scheduler hint is expected when using this constraint:  
        ```max_instances_per_host = <a positive integer>```  
        By default, max_instances_per_host = 1, resulting in an anti-affinity placement solution.  
    
    - **MaxDiskAllocationPerHostConstraint**  
        Cap the virtual disk allocation of hosts.  
        The following option should be set in configuration when using this constraint:  
        ```linearconstraint_disk_allocation_ratio = <a positive real number>``` (virtual-to-physical disk allocation ratio, if >1.0 then over-allocation is allowed.)  
    
    - **MaxRamAllocationPerHostConstraint**  
        Cap the virtual ram allocation of hosts.  
        The following option should be set in configuration when using this constraint:  
        ```linearconstraint_ram_allocation_ratio = <a positive real number>``` (virtual-to-physical ram allocation ratio, if >1.0 then over-allocation is allowed.)  
    
    - **MaxVcpuAllocationPerHostConstraint**  
        Cap the vcpu allocation of hosts.  

Examples
--------

This is an example usage for creating VMs with volume affinity using the solver scheduler.

* Install the solver scheduler.

* Update the nova.conf with following options:

```
# Default driver to use for the scheduler
scheduler_driver = nova.scheduler.solver_scheduler.ConstraintSolverScheduler

# Default solver to use for the solver scheduler
scheduler_host_solver = nova.scheduler.solvers.hosts_pulp_solver_v2.HostsPulpSolver

# Cost functions to use in the linear solver
scheduler_solver_costs = IpDistanceCost

# Weight of each cost (every cost function used should be given a weight.)
scheduler_solver_cost_weights = IpDistanceCost:1.0

# Constraints used in the solver
scheduler_solver_constraints = ActiveHostConstraint, NumHostsPerInstanceConstraint, MaxDiskAllocationPerHostConstraint, MaxRamAllocationPerHostConstraint

# Virtual-to-physical disk allocation ratio
linearconstraint_disk_allocation_ratio = 1.5

# Virtual-to-physical ram allocation ratio
linearconstraint_ram_allocation_ratio = 1.5
```

* Restart nova-scheduler and then do the followings as admin:

* Create multiple volumes at different hosts

* Run the following command to boot a new instance. (The id of a volume you want to use should be provided as scheduler hint.)
```
nova boot --image=<image-id> --flavor=<flavor-id> --hint ip_distance_cost_volume_id_list=<volume-id> <server-name>
```

* The instance should be created at the same host as the chosen volume as long as the host is active and has enough resources.
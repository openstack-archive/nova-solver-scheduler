===============================
OpenStack Nova Solver Scheduler
===============================

A new OpenStack Nova scheduler driver based on constraints-based optimization
solvers.

* Free software: Apache license
* Source: http://git.openstack.org/cgit/stackforge/nova-solver-scheduler
* Bugs: https://bugs.launchpad.net/nova-solver-scheduler 
* Blueprints: https://blueprints.launchpad.net/nova-solver-scheduler

* This is the stable Juno OpenStack compatible version branch.


## Overview  

Solver Scheduler is an OpenStack Nova scheduler driver that provides smart, efficient, and optimization based compute resource scheduling in Nova. It is a pluggable scheduler driver, that can leverage existing constraint solvers available in open source such as PULP, CVXOPT, Google OR-TOOLS, etc. It can be easily extended to add complex constraint models for various use cases, and to solve complex scheduling problems with pulggable solving frameworks.  

## From filter-scheduler to solver-scheduler  

The nova-solver-scheduler works in a similar (but different) way as Nova's default filter-scheduler. It is designed to have the following 3-layer pluggable architecture, compared with filter-scheduler's 2-layer architecture.  

* Filter-scheduler architecture  
  - Scheduler driver: FilterScheduler. This is a driver that realizes the filter based scheduling functionalities. It is plugged into Nova scheduler service, and configured by the second layer plug-in's, which are known as weighers and filters.  
  - Configurable plug-ins: Weights/Filters. They are the configuration units that defines the behaviour of the filter-scheduler, where filters decide which hosts are available for user requested instance, and weights are then used to sort filtered hosts to find a best one to place the instance.  

* Solver-scheduler architecture  
  - Scheduler driver: SolverScheduler. This is a driver that realizes constraint optimization based scheduling functionalities. It sits in parellel with FilterScheduler and can be used as an (advanced) alternative. It uses pluggable opeimization solver modules to solve scheduling problems.  
  - Solver drivers. The solver drivers are pluggavle optimization solvers that solve scheduling problems defined by its lower layer plug-in's, which are costs/constraints. The pluggable solvers provide more flexibility for complex scheduling scenarios as well as the ability to give more optimimal scheduling solutions.  
  - Configurable plug-ins: Costs/Constraints. Similar as weights/filters in the filter-scheduler. The constraints define the hard restrictions of hosts that cannot be violated, and the costs define the soft objectives that the scheduler should tend to achieve. Scheduler solver will give an overall optimized solution for the placement of all requested instances in each single instance creation request. The costs/constraints can be plugged and configured in a similar way as weights/filters in Nova's default filter scheduler.  

While it appears to the user that the solver scheduler with costs/constraints provides similar functionalities as filter scheduler with weights/filters, solver scheduler can be more efficient in large scale high amount scheduling problems (e.g. placing 500 instances in a 1000 node cluster in a single request), the scheduling solution from the solver scheduler is also more optimal compared with that from filter scheduler due to its more flexible designs.
 
## Basic configurations  

In order to enable nova-solver-scheduler, we need to have the following minimal configurations in the "[default]" section of nova.conf. Please overwrite the config options' values if the option keys already exist in the configuration file.  
```
[DEFAULT]
... (other options)
scheduler_driver=nova_solverscheduler.scheduler.solver_scheduler.ConstraintSolverScheduler
scheduler_host_manager=nova_solverscheduler.scheduler.solver_scheduler_host_manager.SolverSchedulerHostManager
```  

## Solvers  

We provide 2 solvers that can plug-in-and-solve the scheduling problems by satisfying all the configured constraints: FastSolver (default), and PulpSolver. The FastSolver runs a fast algorithm that can solve large scale scheduling requests efficiently while giving optimal solutions. The PulpSolver translates the scheduling problems into standard LP (Linear Programming) problems, and invokes a 3rd party LP solver interface (coinor.pulp >= 1.0.4) to solve the scheduling problems. While PulpSolver might be more flexible for complex constraints (which might happen in the future), it works slower than the FastSolver especially in large scale scheduling problems.  
We recommend using FastSolver at the current stage, as it covers all (currently) known constraint requirements, and scales better.  
The following option in the "[solver_scheduler]" section of nova config should be used to specify which solver to use. Please add a new section title called "[solver_scheduler]" if it (probably) doesn't already exist in the nova config file.  

```
[solver_scheduler]
scheduler_host_solver=nova_solverscheduler.scheduler.solvers.fast_solver.FastSolver
```  

## Costs and Constraints  

### Configuring which costs/constraints to use  

Solver-scheduler uses "costs" and "constraints" to configure the behaviour of scheduler. They can be set in a similar way as "weights" and "filters" in the filter-scheduler.  

Here is an example for setting which "costs" to use, pleas put these options in the "[solver_scheduler]" section of nova config, each "cost" has a multiplier associated with it to specify its weight in the scheduler decision:  
```
[solver_scheduler]
... (other options)
scheduler_solver_costs=RamCost,AffinityCost,AntiAffinityCost
ram_cost_multiplier=1.0
affinity_cost_multiplier=2.0
anti_affinity_cost_multiplier=0.5
```  

**Notes**  
Tips about the cost multipliers' values:  

Cost class | Multiplier
---------- | ----------
RamCost | \> 0: the scheduler will tend to balance the usage of RAM. The higher the value, the more weight the cost will get in scheduler's decision.<br>\< 0: the scheduler will tend to stack the RAM usage. The higher the *absolute* value, the more weight the cost will get in scheduler's decision.<br>= 0: the cost will be ignored.
MetricsCost | \> 0: The higher the value, the more weight the cost will get in scheduler's decision.<br>\< 0: Not recommended. Might not make the cost meaningful.<br>= 0: the cost will be ignored.

The followings is an example of how to set which "constraints" to be used by the solver-scheduler.  
```
[solver_scheduler]
... (other options)
scheduler_solver_constraints=ActiveHostsConstraint,RamConstraint,NumInstancesConstraint
```  

In the following section we will discuss the detailed cost and constraint classes.  

### Transition from filter-scheduler to solver-scheduler  

The table below lists supported constraints and their counterparts in filter scheduler. Those costs and constraints can be used in the same way as the weights/filters in the filter scheduler except the above option-setting. Please refer to [OpenStack Configuration Reference](http://docs.openstack.org/icehouse/config-reference/content/section_compute-scheduler.html) for detailed explanation of available weights and filters and their usage instructions.  

Weight | Cost
------ | ----
MetricsWeigher | MetricsCost
RAMWeigher | RamCost

Filter | Constraint
------ | ----------
AggregateCoreFilter | AggregateVcpuConstraint
AggregateDiskFilter | AggregateDiskConstraint
AggregateImagePropertiesIsolation | AggregateImagePropertiesIsolationConstraint
AggregateInstanceExtraSpecsFilter | AggregateInstanceExtraSpecsConstraint
AggregateMultiTenancyIsolation | AggregateMultiTenancyIsolationConstraint
AggregateRamFilter | AggregateRamConstraint
AggregateTypeAffinityFilter | AggregateTypeAffinityConstraint
AllHostsFilter | NoConstraint
AvailabilityZoneFilter | AvailabilityZoneConstraint
ComputeCapabilitiesFilter | ComputeCapabilitiesConstraint
ComputeFilter | ActiveHostsConstraint
CoreFilter | VcpuConstraint
DifferentHostFilter | DifferentHostConstraint
DiskFilter | DiskConstraint
ImagePropertiesFilter | ImagePropertiesConstraint
IsolatedHostsFilter | IsolatedHostsConstraint
IoOpsFilter | IoOpsConstraint
JsonFilter | JsonConstraint
MetricsFilter | MetricsConstraint
NumInstancesFilter | NumInstancesConstraint
PciPassthroughFilter | PciPassthroughConstraint
RamFilter | RamConstraint
RetryFilter | RetryConstraint
SameHostFilter | SameHostConstraint
ServerGroupAffinityFilter | ServerGroupAffinityConstraint
ServerGroupAntiAffinityFilter | ServerGroupAntiAffinityConstraint
SimpleCIDRAffinityFilter | SimpleCidrAffinityConstraint
TrustedFilter | TrustedHostsConstraint
TypeAffinityFilter | TypeAffinityConstraint

**Notes**  
Some of the above constraints directly invoke their filter counterparts to check host availability, others (in the following list) are implemented with improved logic that may result in more optimal placement decisions for multi-instance requests:  
- DiskConstraint
- AggregateDiskConstraint (inherited from DiskConstraint)
- RamConstraint
- AggregateRamConstraint (inherited from RamConstraint)
- VcpuConstraint
- AggregateVcpuConstraint (inherited from VcpuConstraint)
- IoOpsConstraint
- NumInstancesConstraint
- PciPassthroughConstraint
- ServerGroupAffinityConstraint
- ServerGroupAntiAffinityConstraint

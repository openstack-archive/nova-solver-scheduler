Openstack Nova Solver Scheduler
===============================

Solver Scheduler is an Openstack Nova Scheduler driver that provides a smarter, complex constraints optimization based resource scheduling in Nova.  It is a pluggable scheduler driver, that can leverage existing complex constraint solvers available in open source such as PULP, CVXOPT, Google OR-TOOLS, etc. It can be easily extended to add complex constraint models for various use cases, written using any of the available open source constraint solving frameworks. 

Key modules
-----------

* The new scheduler driver module:

    nova/scheduler/solver_scheduler.py

* The code includes a reference implementation of a solver that models the scheduling problem as a Linear Programming model, written using the PULP LP modeling language. It uses a PULP_CBC_CMD, which is a packaged constraint solver, included in the coinor-pulp python package.

    nova/scheduler/solvers/hosts_pulp_solver.py

* The pluggable solvers using coinor-pulp package, where costs functions and linear constraints can be plugged into the solver.

    nova/scheduler/solvers/pluggable_hosts_pulp_solver.py

Additional modules
------------------

* The cost functions pluggable to solver:

    nova/scheduler/solvers/costs/ram_cost.py  
    nova/scheduler/solvers/costs/volume_affinity_cost.py  

* The linear constraints that are pluggable to solver:

    nova/scheduler/solvers/linearconstraints/active_host_constraint.py  
    nova/scheduler/solvers/linearconstraints/all_hosts_constraint.py  
    nova/scheduler/solvers/linearconstraints/availability_zone_constraint.py  
    nova/scheduler/solvers/linearconstraints/different_host_constraint.py  
    nova/scheduler/solvers/linearconstraints/same_host_constraint.py  
    nova/scheduler/solvers/linearconstraints/io_ops_constraint.py  
    nova/scheduler/solvers/linearconstraints/max_disk_allocation_constraint.py  
    nova/scheduler/solvers/linearconstraints/max_ram_allocation_constraint.py  
    nova/scheduler/solvers/linearconstraints/max_vcpu_allocation_constraint.py  
    nova/scheduler/solvers/linearconstraints/max_instances_per_host_constraint.py  
    nova/scheduler/solvers/linearconstraints/non_trivial_solution_constraint.py  

Requirements
------------

* coinor.pulp>=1.0.4

Installation
------------

We provide 2 ways to install the solver-scheduler code. In this section, we will guide you through installing the solver scheduler with the minimum configuration. For instructions of configuring a fully functional solver-scheduler, please check out the next sections.  

* **Note:**  

    - Make sure you have an existing installation of **Openstack Icehouse**.  

    - The automatic installation scripts are of **alpha** version, which was tested on **Ubuntu 14.04** and **OpenStack Icehouse** only.  

    - We recommend that you Do backup at least the following files before installation, because they are to be overwritten or modified:  
        $NOVA_CONFIG_PARENT_DIR/nova.conf  
        $NOVA_PARENT_DIR/nova/volume/cinder.py  
        $NOVA_PARENT_DIR/nova/tests/scheduler/fakes.py  
        (replace the $... with actual directory names.)  

* **Prerequisites**  
    - Please install the python package: coinor.pulp >= 1.0.4  

* **Manual Installation**  

    - Make sure you have performed backups properly.  

    - Clone the repository to your local host where nova-scheduler is run.  

    - Navigate to the local repository and copy the contents in 'nova' sub-directory to the corresponding places in existing nova, e.g.  
      ```cp -r $LOCAL_REPOSITORY_DIR/nova $NOVA_PARENT_DIR```  
      (replace the $... with actual directory name.)  

    - Update the nova configuration file (e.g. /etc/nova/nova.conf) with the minimum option below. If the option already exists, modify its value, otherwise add it to the config file. Check the "Configurations" section below for a full configuration guide.  
      ```
      [DEFAULT]
      ...
      scheduler_driver=nova.scheduler.solver_scheduler.ConstraintSolverScheduler
      ```  

    - Restart the nova scheduler.  
      ```service nova-scheduler restart```  

    - Done. The nova-solver-scheduler should be working with a demo configuration.  

* **Automatic Installation**  

    - Make sure you have performed backups properly.  

    - Clone the repository to your local host where nova-scheduler is run.  

    - Navigate to the installation directory and run installation script.  
      ```
      cd $LOCAL_REPOSITORY_DIR/installation
      sudo bash ./install.sh
      ```  
      (replace the $... with actual directory name.)  

    - Done. The installation code should setup the solver-scheduler with the minimum configuration below. Check the "Configurations" section for a full configuration guide.  
      ```
      [DEFAULT]
      ...
      scheduler_driver=nova.scheduler.solver_scheduler.ConstraintSolverScheduler
      ```  

* **Uninstallation**  

    - If you need to switch to other scheduler, simply open the nova configuration file and edit the option ```scheduler_driver```  (the default: ```scheduler_driver=nova.scheduler.filter_scheduler.FilterScheduler```), then restart nova-scheduler.  

    - There is no need to remove the solver-scheduler code after installation since it is supposed to be fully compatible with the default nova scheduler. However, in case you really want to restore the code, you can either do it manually with your backup, or use the uninstallation script provided in the installation directory.  
      ```
      cd $LOCAL_REPOSITORY_DIR/installation
      sudo bash ./uninstall.sh
      ```  
      (replace the $... with actual directory name.)  

    - Please remember to restart the nova-scheduler service everytime when changes are made in the code or config file.  

* **Troubleshooting**  

    In case the automatic installation/uninstallation process is not complete, please check the followings:  

    - Make sure your OpenStack version is Icehouse.  

    - Check the variables in the beginning of the install.sh/uninstall.sh scripts. Your installation directories may be different from the default values we provide.  

    - The installation code will automatically backup the related codes to:  
      $NOVA_PARENT_DIR/nova/.solver-scheduler-installation-backup  
      Please do not make changes to the backup if you do not have to. If you encounter problems during installation, you can always find the backup files in this directory.  

    - The automatic uninstallation script can only work when you used automatic installation beforehand. If you installed manually, please also uninstall manually (though there is no need to actually "uninstall").  

    - In case the automatic installation does not work, try to install manually.  

Configurations
--------------

* This is a (default) configuration sample for the solver-scheduler. Please add/modify these options in /etc/nova/nova.conf.
* Note:
    - Please carefully make sure that options in the configuration file are not duplicated. If an option name already exists, modify its value instead of adding a new one of the same name.
    - The solver class 'nova.scheduler.solvers.hosts_pulp_solver.HostsPulpSolver' is used by default in installation for demo purpose. It is self-inclusive and non-pluggable for costs and constraints. Please switch to 'nova.scheduler.solvers.pluggable_hosts_pulp_solver.HostsPulpSolver' for a fully functional (pluggable) solver.
    - Please refer to the 'Configuration Details' section below for proper configuration and usage of costs and constraints.

```
[DEFAULT]

...

#
# Options defined in nova.scheduler.manager
#

# Default driver to use for the scheduler (string value)
scheduler_driver=nova.scheduler.solver_scheduler.ConstraintSolverScheduler

#
# Options defined in nova.scheduler.filters.core_filter
#

# Virtual CPU to physical CPU allocation ratio which affects
# all CPU filters. This configuration specifies a global ratio
# for CoreFilter. For AggregateCoreFilter, it will fall back
# to this configuration value if no per-aggregate setting
# found. This option is also used in Solver Scheduler for the
# MaxVcpuAllocationPerHostConstraint  (floating point value)
cpu_allocation_ratio=16.0

#
# Options defined in nova.scheduler.filters.disk_filter
#

# Virtual disk to physical disk allocation ratio (floating
# point value)
disk_allocation_ratio=1.0

#
# Options defined in nova.scheduler.filters.num_instances_filter
#

# Ignore hosts that have too many instances (integer value)
max_instances_per_host=50

#
# Options defined in nova.scheduler.filters.io_ops_filter
#

# Ignore hosts that have too many
# builds/resizes/snaps/migrations. (integer value)
max_io_ops_per_host=8

#
# Options defined in nova.scheduler.filters.ram_filter
#

# Virtual ram to physical ram allocation ratio which affects
# all ram filters. This configuration specifies a global ratio
# for RamFilter. For AggregateRamFilter, it will fall back to
# this configuration value if no per-aggregate setting found.
# (floating point value)
ram_allocation_ratio=1.5

#
# Options defined in nova.scheduler.weights.ram
#

# Multiplier used for weighing ram.  Negative numbers mean to
# stack vs spread. (floating point value)
ram_weight_multiplier=1.0

#
# Options defined in nova.volume.cinder
#

# Keystone Cinder account username (string value)
cinder_admin_user=<None>

# Keystone Cinder account password (string value)
cinder_admin_password=<None>

# Keystone Cinder account tenant name (string value)
cinder_admin_tenant_name=service

# Complete public Identity API endpoint (string value)
cinder_auth_uri=<None>


[solver_scheduler]

#
# Options defined in nova.scheduler.solver_scheduler
#

# The pluggable solver implementation to use. By default, a
# reference solver implementation is included that models the
# problem as a Linear Programming (LP) problem using PULP.
# To use a fully functional (pluggable) solver, set the option as
# "nova.scheduler.solvers.pluggable_hosts_pulp_solver.HostsPulpSolver"
# (string value)
scheduler_host_solver=nova.scheduler.solvers.pluggable_hosts_pulp_solver.HostsPulpSolver


#
# Options defined in nova.scheduler.solvers
#

# Which constraints to use in scheduler solver (list value)
scheduler_solver_constraints=ActiveHostConstraint, NonTrivialSolutionConstraint

# Assign weight for each cost (list value)
scheduler_solver_cost_weights=RamCost:1.0

# Which cost matrices to use in the scheduler solver.
# (list value)
scheduler_solver_costs=RamCost

```

Configuration Details
---------------------

* Available costs  

    - **RamCost**  
        Help to balance (or stack) ram usage of hosts.  
        The following option should be set in configuration when using this cost:  
        ```
        ram_weight_multiplier = <a real number>
        ram_allocation_ratio = <a float value>
        ```  
        set the multiplier to negative number for balanced ram usage,  
        set the multiplier to positive number for stacked ram usage.  
    
    - **VolumeAffinityCost**  
        Help to place instances at the same host as a specific volume, if possible.  
        In order to use this cost, you need to pass a hint to the scheduler on booting a server.  
        ```nova boot ... --hint affinity_volume_id=<id of the affinity volume> ...```  
        You also need to have the following options set in the '[DEFAULT]' section of the configuration.  
        ```
        cinder_admin_user=<cinder username>
        cinder_admin_password=<cinder password>
        cinder_admin_tenant_name=<cinder tenant name>
        cinder_auth_uri=<the identity api endpoint>
        ```  

* Available linear constraints  

    - **ActiveHostConstraint**  
        By enabling this constraint, only enabled and operational hosts are allowed to be selected.  
        Normally this constraint should always be enabled.  
    
    - **NonTrivialSolutionConstraint**  
        The purpose of this constraint is to avoid trivial solution (i.e. instances placed nowhere).  
        Normally this constraint should always be enabled.
    
    - **MaxRamAllocationPerHostConstraint**  
        Cap the virtual ram allocation of hosts.  
        The following option should be set in configuration when using this constraint:  
        ```ram_allocation_ratio = <a positive real number>``` (virtual-to-physical ram allocation ratio, if >1.0 then over-allocation is allowed.)  
    
    - **MaxDiskAllocationPerHostConstraint**  
        Cap the virtual disk allocation of hosts.  
        The following option should be set in configuration when using this constraint:  
        ```disk_allocation_ratio = <a positive real number>``` (virtual-to-physical disk allocation ratio, if >1.0 then over-allocation is allowed.)  
    
    - **MaxVcpuAllocationPerHostConstraint**  
        Cap the vcpu allocation of hosts.  
        The following option should be set in configuration when using this constraint:  
        ```cpu_allocation_ratio = <a positive real number>``` (virtual-to-physical cpu allocation ratio, if >1.0 then over-allocation is allowed.)  
    
    - **NumInstancesPerHostConstraint**  
        Specify the maximum number of instances that can be placed in each host.  
        The following option is expected in the configuration:  
        ```max_instances_per_host = <a positive integer>```  
    
    - **DifferentHostConstraint**  
        Force instances to be placed at different hosts as specified instance(s).  
        The following scheduler hint is expected when using this constraint:  
        ```different_host = <a (list of) instance uuid(s)>```  
    
    - **SameHostConstraint**  
        Force instances to be placed at same hosts as specified instance(s).  
        The following scheduler hint is expected when using this constraint:  
        ```same_host = <a (list) of instance uuid(s)>```  
    
    - **AvailablilityZoneConstraint**  
        Select hosts belongong to an availability zone.  
        The following option should be set in configuration when using this constraint:  
        ```default_availability_zone = <availability zone>```  
    
    - **IoOpsConstraint**  
        Ensure the concurrent I/O operations number of selected hosts are within a threshold.  
        The following option should be set in configuration when using this constraint:  
        ```max_io_ops_per_host = <a positive number>```

Examples
--------

This is an example usage for creating VMs with volume affinity using the solver scheduler.

* Install the solver scheduler.

* Update the nova.conf with following options:

```
[DEFAULT]
...
# Default driver to use for the scheduler
scheduler_driver = nova.scheduler.solver_scheduler.ConstraintSolverScheduler

# Virtual-to-physical disk allocation ratio
disk_allocation_ratio = 1.0

# Virtual-to-physical ram allocation ratio
ram_allocation_ratio = 1.5

# Keystone Cinder account username (string value)
cinder_admin_user=<cinder username>

# Keystone Cinder account password (string value)
cinder_admin_password=<cinder password>

# Keystone Cinder account tenant name (string value)
cinder_admin_tenant_name=<cinder tenant name>

# Complete public Identity API endpoint (string value)
cinder_auth_uri=<the identity api endpoint, e.g. "http://controller:5000/v2.0">


[solver_scheduler]

# Default solver to use for the solver scheduler
scheduler_host_solver = nova.scheduler.solvers.pluggable_hosts_pulp_solver.HostsPulpSolver

# Cost functions to use in the linear solver
scheduler_solver_costs = VolumeAffinityCost

# Weight of each cost (every cost function used should be given a weight.)
scheduler_solver_cost_weights = VolumeAffinityCost:1.0

# Constraints used in the solver
scheduler_solver_constraints = ActiveHostConstraint, NonTrivialSolutionConstraint, MaxDiskAllocationPerHostConstraint, MaxRamAllocationPerHostConstraint

```

* Restart nova-scheduler and then do the followings:

* Create multiple volumes at different hosts

* Run the following command to boot a new instance. (The id of a volume you want to use should be provided as scheduler hint.)
```
nova boot --image=<image-id> --flavor=<flavor-id> --hint affinity_volume_id=<volume-id> <server-name>
```

* The instance should be created at the same host as the chosen volume as long as the host is active and has enough resources.

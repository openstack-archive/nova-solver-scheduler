# Copyright 2011 OpenStack Foundation
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
Fakes For Scheduler tests.
"""

from nova.compute import vm_states
from nova import db
from nova import objects
from nova_solverscheduler.scheduler import solver_scheduler
from nova_solverscheduler.scheduler import solver_scheduler_host_manager


NUMA_TOPOLOGY = objects.NUMATopology(
                           cells=[objects.NUMACell(
                                      id=0, cpuset=set([1, 2]), memory=512,
                               cpu_usage=0, memory_usage=0, mempages=[],
                               siblings=[], pinned_cpus=set([])),
                                  objects.NUMACell(
                                      id=1, cpuset=set([3, 4]), memory=512,
                                cpu_usage=0, memory_usage=0, mempages=[],
                               siblings=[], pinned_cpus=set([]))])

COMPUTE_NODES = [
        dict(id=1, local_gb=1024, memory_mb=1024, vcpus=1,
             disk_available_least=None, free_ram_mb=512, vcpus_used=1,
             free_disk_gb=512, local_gb_used=0, updated_at=None,
             service=dict(host='host1', disabled=False),
             hypervisor_hostname='node1', host_ip='127.0.0.1',
             hypervisor_version=0),
        dict(id=2, local_gb=2048, memory_mb=2048, vcpus=2,
             disk_available_least=1024, free_ram_mb=1024, vcpus_used=2,
             free_disk_gb=1024, local_gb_used=0, updated_at=None,
             service=dict(host='host2', disabled=True),
             hypervisor_hostname='node2', host_ip='127.0.0.1',
             hypervisor_version=0),
        dict(id=3, local_gb=4096, memory_mb=4096, vcpus=4,
             disk_available_least=3333, free_ram_mb=3072, vcpus_used=1,
             free_disk_gb=3072, local_gb_used=0, updated_at=None,
             service=dict(host='host3', disabled=False),
             hypervisor_hostname='node3', host_ip='127.0.0.1',
             hypervisor_version=0),
        dict(id=4, local_gb=8192, memory_mb=8192, vcpus=8,
             disk_available_least=8192, free_ram_mb=8192, vcpus_used=0,
             free_disk_gb=8888, local_gb_used=0, updated_at=None,
             service=dict(host='host4', disabled=False),
             hypervisor_hostname='node4', host_ip='127.0.0.1',
             hypervisor_version=0),
        # Broken entry
        dict(id=5, local_gb=1024, memory_mb=1024, vcpus=1, service=None),
]

COMPUTE_NODES_OBJ = [
        objects.ComputeNode(
            id=1, local_gb=1024, memory_mb=1024, vcpus=1,
            disk_available_least=None, free_ram_mb=512, vcpus_used=1,
            free_disk_gb=512, local_gb_used=0, updated_at=None,
            host='host1', hypervisor_hostname='node1', host_ip='127.0.0.1',
            hypervisor_version=0, numa_topology=None,
            hypervisor_type='foo', supported_hv_specs=[],
            pci_device_pools=None, cpu_info=None, stats=None, metrics=None),
        objects.ComputeNode(
            id=2, local_gb=2048, memory_mb=2048, vcpus=2,
            disk_available_least=1024, free_ram_mb=1024, vcpus_used=2,
            free_disk_gb=1024, local_gb_used=0, updated_at=None,
            host='host2', hypervisor_hostname='node2', host_ip='127.0.0.1',
            hypervisor_version=0, numa_topology=None,
            hypervisor_type='foo', supported_hv_specs=[],
            pci_device_pools=None, cpu_info=None, stats=None, metrics=None),
        objects.ComputeNode(
            id=3, local_gb=4096, memory_mb=4096, vcpus=4,
            disk_available_least=3333, free_ram_mb=3072, vcpus_used=1,
            free_disk_gb=3072, local_gb_used=0, updated_at=None,
            host='host3', hypervisor_hostname='node3', host_ip='127.0.0.1',
            hypervisor_version=0, numa_topology=NUMA_TOPOLOGY._to_json(),
            hypervisor_type='foo', supported_hv_specs=[],
            pci_device_pools=None, cpu_info=None, stats=None, metrics=None),
        objects.ComputeNode(
            id=4, local_gb=8192, memory_mb=8192, vcpus=8,
            disk_available_least=8192, free_ram_mb=8192, vcpus_used=0,
            free_disk_gb=8888, local_gb_used=0, updated_at=None,
            host='host4', hypervisor_hostname='node4', host_ip='127.0.0.1',
            hypervisor_version=0, numa_topology=None,
            hypervisor_type='foo', supported_hv_specs=[],
            pci_device_pools=None, cpu_info=None, stats=None, metrics=None),
        # Broken entry
        objects.ComputeNode(
            id=5, local_gb=1024, memory_mb=1024, vcpus=1,
            host='fake', hypervisor_hostname='fake-hyp'),
]

INSTANCES = [
        dict(root_gb=512, ephemeral_gb=0, memory_mb=512, vcpus=1,
             host='host1', node='node1'),
        dict(root_gb=512, ephemeral_gb=0, memory_mb=512, vcpus=1,
             host='host2', node='node2'),
        dict(root_gb=512, ephemeral_gb=0, memory_mb=512, vcpus=1,
             host='host2', node='node2'),
        dict(root_gb=1024, ephemeral_gb=0, memory_mb=1024, vcpus=1,
             host='host3', node='node3'),
        # Broken host
        dict(root_gb=1024, ephemeral_gb=0, memory_mb=1024, vcpus=1,
             host=None),
        # No matching host
        dict(root_gb=1024, ephemeral_gb=0, memory_mb=1024, vcpus=1,
             host='host5', node='node5'),
]

SERVICES = [
        objects.Service(host='host1', disabled=False),
        objects.Service(host='host2', disabled=True),
        objects.Service(host='host3', disabled=False),
        objects.Service(host='host4', disabled=False),
]


class FakeSolverScheduler(solver_scheduler.ConstraintSolverScheduler):
    def __init__(self, *args, **kwargs):
        super(FakeSolverScheduler, self).__init__(*args, **kwargs)
        self.host_manager = (
                solver_scheduler_host_manager.SolverSchedulerHostManager())


class FakeSolverSchedulerHostManager(
        solver_scheduler_host_manager.SolverSchedulerHostManager):
    """host1: free_ram_mb=1024-512-512=0, free_disk_gb=1024-512-512=0
       host2: free_ram_mb=2048-512=1536  free_disk_gb=2048-512=1536
       host3: free_ram_mb=4096-1024=3072  free_disk_gb=4096-1024=3072
       host4: free_ram_mb=8192  free_disk_gb=8192
    """

    def __init__(self):
        super(FakeSolverSchedulerHostManager, self).__init__()

        self.service_states = {
            'host1': {
                'compute': {'host_memory_free': 1073741824},
            },
            'host2': {
                'compute': {'host_memory_free': 2147483648},
            },
            'host3': {
                'compute': {'host_memory_free': 3221225472},
            },
            'host4': {
                'compute': {'host_memory_free': 999999999},
            },
        }


class FakeSolverSchedulerHostState(
        solver_scheduler_host_manager.SolverSchedulerHostState):
    def __init__(self, host, node, attribute_dict):
        super(FakeSolverSchedulerHostState, self).__init__(host, node)
        for (key, val) in attribute_dict.iteritems():
            setattr(self, key, val)


class FakeInstance(object):
    def __init__(self, context=None, params=None):
        """Create a test instance. Returns uuid."""
        self.context = context

        i = self._create_fake_instance(params=params)
        self.uuid = i['uuid']

    def _create_fake_instance(self, params=None):
        """Create a test instance."""
        if not params:
            params = {}

        inst = {}
        inst['vm_state'] = vm_states.ACTIVE
        inst['image_ref'] = 1
        inst['reservation_id'] = 'r-fakeres'
        inst['user_id'] = 'fake'
        inst['project_id'] = 'fake'
        inst['instance_type_id'] = 2
        inst['ami_launch_index'] = 0
        inst.update(params)
        return db.instance_create(self.context, inst)


class FakeComputeAPI(object):
    def create_db_entry_for_new_instance(self, *args, **kwargs):
        pass

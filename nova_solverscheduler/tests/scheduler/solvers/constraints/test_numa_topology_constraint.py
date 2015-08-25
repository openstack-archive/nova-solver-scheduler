# Copyright (c) 2015 Cisco Systems Inc.
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

import mock
from oslo_serialization import jsonutils

from nova import objects
from nova.objects import base as obj_base
from nova import test
from nova.tests.unit import fake_instance
from nova_solverscheduler.scheduler.solvers.constraints \
        import numa_topology_constraint
from nova_solverscheduler.tests.scheduler import solver_scheduler_fakes \
        as fakes

NUMA_TOPOLOGY = objects.NUMATopology(
    cells=[
        objects.NUMACell(id=0, cpuset=set([1, 2]), memory=512,
                        cpu_usage=0, memory_usage=0, mempages=[],
                        siblings=[], pinned_cpus=set([])),
        objects.NUMACell(id=1, cpuset=set([3, 4]), memory=512,
                        cpu_usage=0, memory_usage=0, mempages=[],
                        siblings=[], pinned_cpus=set([]))
    ]
)


class TestNUMATopologyConstraint(test.NoDBTestCase):

    def setUp(self):
        super(TestNUMATopologyConstraint, self).setUp()
        self.constraint_cls = numa_topology_constraint.NUMATopologyConstraint

    def _gen_fake_hosts(self):
        host1 = fakes.FakeSolverSchedulerHostState('host1', 'node1',
            {
                'numa_topology': objects.NUMATopology(
                    cells=[
                        objects.NUMACell(id=0, cpuset=set([1, 2]),
                            memory=1024, cpu_usage=0, memory_usage=0,
                            mempages=[], siblings=[], pinned_cpus=set([])),
                        objects.NUMACell(id=1, cpuset=set([3, 4]),
                            memory=1024, cpu_usage=0, memory_usage=0,
                            mempages=[], siblings=[], pinned_cpus=set([]))]),
                'pci_stats': None
            })
        host2 = fakes.FakeSolverSchedulerHostState('host2', 'node1',
            {
                'numa_topology': objects.NUMATopology(
                    cells=[
                        objects.NUMACell(id=0, cpuset=set([1, 2]),
                            memory=1024, cpu_usage=0, memory_usage=0,
                            mempages=[], siblings=[], pinned_cpus=set([])),
                        objects.NUMACell(id=1, cpuset=set([3, 4]),
                            memory=512, cpu_usage=0, memory_usage=0,
                            mempages=[], siblings=[], pinned_cpus=set([]))]),
                'pci_stats': None
            })
        host3 = fakes.FakeSolverSchedulerHostState('host3', 'node1',
            {
                'numa_topology': objects.NUMATopology(
                    cells=[
                        objects.NUMACell(id=0, cpuset=set([1, 2]),
                            memory=512, cpu_usage=0, memory_usage=0,
                            mempages=[], siblings=[], pinned_cpus=set([])),
                        objects.NUMACell(id=1, cpuset=set([3]),
                            memory=512, cpu_usage=0, memory_usage=0,
                            mempages=[], siblings=[], pinned_cpus=set([]))]),
                'pci_stats': None
            })
        hosts = [host1, host2, host3]
        return hosts

    def test_get_constraint_matrix(self):
        self.flags(ram_allocation_ratio=1)
        self.flags(cpu_allocation_ratio=2)

        instance_topology = objects.InstanceNUMATopology(cells=[
                objects.InstanceNUMACell(id=0, cpuset=set([1, 2]), memory=512),
                objects.InstanceNUMACell(id=1, cpuset=set([3, 4]), memory=512)]
        )
        instance = fake_instance.fake_instance_obj(mock.sentinel.ctx,
                root_gb=0, ephemeral_gb=0, memory_mb=0, vcpus=0,)
        instance.numa_topology = instance_topology
        filter_properties = {
            'request_spec': {
                'instance_properties': jsonutils.to_primitive(
                    obj_base.obj_to_primitive(instance))},
            'num_instances': 2}
        fake_hosts = self._gen_fake_hosts()

        expected_cons_mat = [
            [True, True],
            [True, False],
            [False, False]]

        cons_mat = self.constraint_cls().get_constraint_matrix(
                fake_hosts, filter_properties)

        self.assertEqual(expected_cons_mat, cons_mat)

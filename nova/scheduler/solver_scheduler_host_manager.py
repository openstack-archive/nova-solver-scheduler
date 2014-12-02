# Copyright (c) 2011 OpenStack Foundation
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
Manage hosts in the current zone.
"""

from oslo.config import cfg

from nova.compute import task_states
from nova.compute import vm_states
from nova import db
from nova.objects import aggregate as aggregate_obj
from nova.objects import instance as instance_obj
from nova.openstack.common.gettextutils import _
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging
from nova.openstack.common import timeutils
from nova.pci import pci_request
from nova.pci import pci_stats
from nova.scheduler import host_manager

physnet_config_file_opts = [
    cfg.StrOpt('physnet_config_file',
            default='/etc/neutron/plugins/ml2/ml2_conf_cisco.ini',
            help='The config file specifying the physical network topology')
    ]

CONF = cfg.CONF
CONF.import_opt('scheduler_available_filters', 'nova.scheduler.host_manager')
CONF.import_opt('scheduler_default_filters', 'nova.scheduler.host_manager')
CONF.import_opt('scheduler_weight_classes', 'nova.scheduler.host_manager')
CONF.register_opts(physnet_config_file_opts)

LOG = logging.getLogger(__name__)


class HostState(host_manager.HostState):
    """Mutable and immutable information tracked for a host.
    This is an attempt to remove the ad-hoc data structures
    previously used and lock down access.
    """

    def __init__(self, *args, **kwargs):
        super(HostState, self).__init__(*args, **kwargs)
        self.projects = []
        # For network constraints
        # NOTE(Xinyuan): currently for POC only, and may require Neurtron
        self.networks = []
        self.physnet_config = []
        self.rack_networks = []
        # For host aggregate constraints
        self.host_aggregates_stats = {}

    def update_from_hosted_instances(self, context, compute):
        service = compute['service']
        if not service:
            LOG.warn(_("No service for compute ID %s") % compute['id'])
            return
        host = service['host']
        # retrieve instances for each hosts to extract needed infomation
        # NOTE: ideally we should use get_by_host_and_node, but there's a bug
        # in the Icehouse release, that doesn't allow 'expected_attrs' here.
        instances = instance_obj.InstanceList.get_by_host(context, host,
                    expected_attrs=['info_cache'])
        # get hosted networks
        # NOTE(Xinyuan): POC.
        instance_networks = []
        for inst in instances:
            network_info = inst.get('info_cache', {}).get('network_info', [])
            instance_networks.extend([vif['network']['id']
                                        for vif in network_info])
        self.networks = list(set(instance_networks))

    def update_from_compute_node(self, compute):
        """Update information about a host from its compute_node info."""
        if (self.updated and compute['updated_at']
                and self.updated > compute['updated_at']):
            return
        all_ram_mb = compute['memory_mb']

        # Assume virtual size is all consumed by instances if use qcow2 disk.
        free_gb = compute['free_disk_gb']
        least_gb = compute.get('disk_available_least')
        if least_gb is not None:
            if least_gb > free_gb:
                # can occur when an instance in database is not on host
                LOG.warn(_("Host has more disk space than database expected"
                           " (%(physical)sgb > %(database)sgb)") %
                         {'physical': least_gb, 'database': free_gb})
            free_gb = min(least_gb, free_gb)
        free_disk_mb = free_gb * 1024

        self.disk_mb_used = compute['local_gb_used'] * 1024

        #NOTE(jogo) free_ram_mb can be negative
        self.free_ram_mb = compute['free_ram_mb']
        self.total_usable_ram_mb = all_ram_mb
        self.total_usable_disk_gb = compute['local_gb']
        self.free_disk_mb = free_disk_mb
        self.vcpus_total = compute['vcpus']
        self.vcpus_used = compute['vcpus_used']
        self.updated = compute['updated_at']
        if 'pci_stats' in compute:
            self.pci_stats = pci_stats.PciDeviceStats(compute['pci_stats'])
        else:
            self.pci_stats = None

        # All virt drivers report host_ip
        self.host_ip = compute['host_ip']
        self.hypervisor_type = compute.get('hypervisor_type')
        self.hypervisor_version = compute.get('hypervisor_version')
        self.hypervisor_hostname = compute.get('hypervisor_hostname')
        self.cpu_info = compute.get('cpu_info')
        if compute.get('supported_instances'):
            self.supported_instances = jsonutils.loads(
                    compute.get('supported_instances'))

        # Don't store stats directly in host_state to make sure these don't
        # overwrite any values, or get overwritten themselves. Store in self so
        # filters can schedule with them.
        stats = compute.get('stats', None) or '{}'
        self.stats = jsonutils.loads(stats)

        self.hypervisor_version = compute['hypervisor_version']

        # Track number of instances on host
        self.num_instances = int(self.stats.get('num_instances', 0))

        # Track number of instances by project_id
        project_id_keys = [k for k in self.stats.keys() if
                k.startswith("num_proj_")]
        for key in project_id_keys:
            project_id = key[9:]
            self.num_instances_by_project[project_id] = int(self.stats[key])

        # Track number of instances in certain vm_states
        vm_state_keys = [k for k in self.stats.keys() if
                k.startswith("num_vm_")]
        for key in vm_state_keys:
            vm_state = key[7:]
            self.vm_states[vm_state] = int(self.stats[key])

        # Track number of instances in certain task_states
        task_state_keys = [k for k in self.stats.keys() if
                k.startswith("num_task_")]
        for key in task_state_keys:
            task_state = key[9:]
            self.task_states[task_state] = int(self.stats[key])

        # Track number of instances by host_type
        os_keys = [k for k in self.stats.keys() if
                k.startswith("num_os_type_")]
        for key in os_keys:
            os = key[12:]
            self.num_instances_by_os_type[os] = int(self.stats[key])

        # Track the number of projects on host
        self.projects = [k[9:] for k in self.stats.keys() if
                        k.startswith("num_proj_") and int(self.stats[k]) > 0]

        self.num_io_ops = int(self.stats.get('io_workload', 0))

        # update metrics
        self._update_metrics_from_compute_node(compute)

    def consume_from_instance(self, instance):
        """Incrementally update host state from an instance."""
        disk_mb = (instance['root_gb'] + instance['ephemeral_gb']) * 1024
        ram_mb = instance['memory_mb']
        vcpus = instance['vcpus']
        self.free_ram_mb -= ram_mb
        self.free_disk_mb -= disk_mb
        self.vcpus_used += vcpus
        self.updated = timeutils.utcnow()

        # Track number of instances on host
        self.num_instances += 1

        # Track number of instances by project_id
        project_id = instance.get('project_id')
        if project_id not in self.num_instances_by_project:
            self.num_instances_by_project[project_id] = 0
        self.num_instances_by_project[project_id] += 1

        # Track number of instances in certain vm_states
        vm_state = instance.get('vm_state', vm_states.BUILDING)
        if vm_state not in self.vm_states:
            self.vm_states[vm_state] = 0
        self.vm_states[vm_state] += 1

        # Track number of instances in certain task_states
        task_state = instance.get('task_state')
        if task_state not in self.task_states:
            self.task_states[task_state] = 0
        self.task_states[task_state] += 1

        # Track number of instances by host_type
        os_type = instance.get('os_type')
        if os_type not in self.num_instances_by_os_type:
            self.num_instances_by_os_type[os_type] = 0
        self.num_instances_by_os_type[os_type] += 1

        pci_requests = pci_request.get_instance_pci_requests(instance)
        if pci_requests and self.pci_stats:
            self.pci_stats.apply_requests(pci_requests)

        vm_state = instance.get('vm_state', vm_states.BUILDING)
        task_state = instance.get('task_state')
        if vm_state == vm_states.BUILDING or task_state in [
                task_states.RESIZE_MIGRATING, task_states.REBUILDING,
                task_states.RESIZE_PREP, task_states.IMAGE_SNAPSHOT,
                task_states.IMAGE_BACKUP]:
            self.num_io_ops += 1

        # Track the number of projects
        project_id = instance.get('project_id')
        if project_id not in self.projects:
            self.projects.append(project_id)

        # Track aggregate stats
        project_id = instance.get('project_id')
        for aggr in self.host_aggregates_stats:
            aggregate_project_list = self.host_aggregates_stats[aggr].get(
                                    'projects', [])
            if project_id not in aggregate_project_list:
                self.host_aggregates_stats[aggr]['projects'].append(project_id)

    def update_from_networks(self, requested_networks):
        for network_id, fixed_ip, port_id in requested_networks:
            if network_id:
                if network_id not in self.networks:
                    self.networks.append(network_id)
                    if not network_id not in self.aggregated_networks:
                        for device in self.aggregated_networks:
                            self.aggregated_networks[device].append(network_id)
                    # do this for host aggregates
                    for aggr in self.host_aggregates_stats:
                        host_aggr_network_list = self.host_aggregates_stats[
                                                    aggr].get('networks', [])
                        if network_id not in host_aggr_network_list:
                            self.host_aggregates_stats[aggr][
                                    'networks'].append(network_id)

    def __repr__(self):
        return ("(%s, %s) ram:%s disk:%s io_ops:%s instances:%s "
                "physnet_config:%s networks:%s rack_networks:%s "
                "projects:%s aggregate_stats:%s" %
                (self.host, self.nodename, self.free_ram_mb, self.free_disk_mb,
                 self.num_io_ops, self.num_instances, self.physnet_config,
                 self.networks, self.rack_networks, self.projects,
                 self.host_aggregates_stats))


class SolverSchedulerHostManager(host_manager.HostManager):
    """HostManager class for solver scheduler."""

    # Can be overridden in a subclass
    host_state_cls = HostState

    def __init__(self, *args, **kwargs):
        super(SolverSchedulerHostManager, self).__init__(*args, **kwargs)

    def get_hosts_stripping_ignored_and_forced(self, hosts,
            filter_properties):
        """Filter hosts by stripping any ignored hosts and
           matching any forced hosts or nodes.
        """

        def _strip_ignore_hosts(host_map, hosts_to_ignore):
            ignored_hosts = []
            for host in hosts_to_ignore:
                for (hostname, nodename) in host_map.keys():
                    if host == hostname:
                        del host_map[(hostname, nodename)]
                        ignored_hosts.append(host)
            ignored_hosts_str = ', '.join(ignored_hosts)
            msg = _('Host filter ignoring hosts: %s')
            LOG.audit(msg % ignored_hosts_str)

        def _match_forced_hosts(host_map, hosts_to_force):
            forced_hosts = []
            for (hostname, nodename) in host_map.keys():
                if hostname not in hosts_to_force:
                    del host_map[(hostname, nodename)]
                else:
                    forced_hosts.append(hostname)
            if host_map:
                forced_hosts_str = ', '.join(forced_hosts)
                msg = _('Host filter forcing available hosts to %s')
            else:
                forced_hosts_str = ', '.join(hosts_to_force)
                msg = _("No hosts matched due to not matching "
                        "'force_hosts' value of '%s'")
            LOG.audit(msg % forced_hosts_str)

        def _match_forced_nodes(host_map, nodes_to_force):
            forced_nodes = []
            for (hostname, nodename) in host_map.keys():
                if nodename not in nodes_to_force:
                    del host_map[(hostname, nodename)]
                else:
                    forced_nodes.append(nodename)
            if host_map:
                forced_nodes_str = ', '.join(forced_nodes)
                msg = _('Host filter forcing available nodes to %s')
            else:
                forced_nodes_str = ', '.join(nodes_to_force)
                msg = _("No nodes matched due to not matching "
                        "'force_nodes' value of '%s'")
            LOG.audit(msg % forced_nodes_str)

        ignore_hosts = filter_properties.get('ignore_hosts', [])
        force_hosts = filter_properties.get('force_hosts', [])
        force_nodes = filter_properties.get('force_nodes', [])

        if ignore_hosts or force_hosts or force_nodes:
            # NOTE(deva): we can't assume "host" is unique because
            #             one host may have many nodes.
            name_to_cls_map = dict([((x.host, x.nodename), x) for x in hosts])
            if ignore_hosts:
                _strip_ignore_hosts(name_to_cls_map, ignore_hosts)
                if not name_to_cls_map:
                    return []
            # NOTE(deva): allow force_hosts and force_nodes independently
            if force_hosts:
                _match_forced_hosts(name_to_cls_map, force_hosts)
            if force_nodes:
                _match_forced_nodes(name_to_cls_map, force_nodes)
            hosts = name_to_cls_map.itervalues()

        return hosts

    def get_filtered_hosts(self, hosts, filter_properties,
            filter_class_names=None, index=0):
        """Filter hosts and return only ones passing all filters."""
        # NOTE(Yathi): Calling the method to apply ignored and forced options
        hosts = self.get_hosts_stripping_ignored_and_forced(hosts,
                         filter_properties)

        force_hosts = filter_properties.get('force_hosts', [])
        force_nodes = filter_properties.get('force_nodes', [])

        if force_hosts or force_nodes:
            # NOTE: Skip filters when forcing host or node
            return list(hosts)

        filter_classes = self._choose_host_filters(filter_class_names)

        return self.filter_handler.get_filtered_objects(filter_classes,
                hosts, filter_properties, index)

    def _get_aggregate_stats(self, context, host_state_map):
        """Update certain stats for the aggregates of the hosts."""
        aggregates = aggregate_obj.AggregateList.get_all(context)
        host_state_list_map = {}

        for (host, node) in host_state_map.keys():
            current_list = host_state_list_map.get(host, None)
            state = host_state_map[(host, node)]
            if not current_list:
                host_state_list_map[host] = [state]
            else:
                host_state_list_map[host] = current_list.append(state)

        for aggregate in aggregates:
            hosts = aggregate.hosts
            projects = set()
            networks = set()
            # Collect all the projects from all the member hosts
            aggr_host_states = []
            for host in hosts:
                host_state_list = host_state_list_map.get(host, None) or []
                aggr_host_states += host_state_list
                for host_state in host_state_list:
                    projects = projects.union(host_state.projects)
                    networks = networks.union(host_state.networks)
            aggregate_stats = {'hosts': hosts,
                                'projects': list(projects),
                                'networks': list(networks),
                                'metadata': aggregate.metadata}
            # Now set this value to all the member host_states
            for host_state in aggr_host_states:
                host_state.host_aggregates_stats[
                                  aggregate.name] = aggregate_stats

    def _get_rack_states(self, context, host_state_map):
        """Retrieve the physical and virtual network states of the hosts.
        """
        def _get_physnet_mappings():
            """Get physical network topologies from a Neutron config file.
            This is a hard-coded function which only supports Cisco Nexus
            driver for Neutron ML2 plugin currently.
            """
            # NOTE(Xinyuan): This feature is for POC only!
            # TODO(Xinyuan): further works are required in implementing
            # Neutron API extensions to get related information.
            host2device_map = {}
            device2host_map = {}
            sections = {}

            state_keys = host_state_map.keys()
            hostname_list = [host for (host, node) in state_keys]

            try:
                physnet_config_parser = cfg.ConfigParser(
                        CONF.physnet_config_file, sections)
                physnet_config_parser.parse()
            except Exception:
                LOG.warn(_("Physnet config file was not parsed properly."))
            # Example section:
            # [ml2_mech_cisco_nexus:1.1.1.1]
            # compute1=1/1
            # compute2=1/2
            # ssh_port=22
            # username=admin
            # password=mySecretPassword
            for parsed_item in sections.keys():
                dev_id, sep, dev_ip = parsed_item.partition(':')
                if dev_id.lower() == 'ml2_mech_cisco_nexus':
                    for key, value in sections[parsed_item].items():
                        if key in hostname_list:
                            hostname = key
                            portid = value[0]
                            host2device_map.setdefault(hostname, [])
                            host2device_map[hostname].append((dev_ip, portid))
                            device2host_map.setdefault(dev_ip, [])
                            device2host_map[dev_ip].append((hostname, portid))
            return host2device_map, device2host_map

        def _get_rack_networks(host_dev_map, dev_host_map, host_state_map):
            """Aggregate the networks associated with a group of hosts in
            same physical groups (e.g. under same ToR switches...)
            """
            rack_networks = {}

            if not dev_host_map or not host_dev_map:
                return rack_networks

            host_networks = {}
            for state_key in host_state_map.keys():
                (host, node) = state_key
                host_state = host_state_map[state_key]
                host_networks.setdefault(host, set())
                host_networks[host] = host_networks[host].union(
                                                        host_state.networks)

            # aggregate hosted networks for each upper level device
            dev_networks = {}
            for dev_id in dev_host_map.keys():
                current_dev_networks = set()
                for (host_name, port_id) in dev_host_map[dev_id]:
                    current_dev_networks = current_dev_networks.union(
                            host_networks.get(host_name, []))
            dev_networks[dev_id] = list(current_dev_networks)

            # make aggregated networks list for each hosts
            for host_name in host_dev_map.keys():
                dev_list = list(set([dev_id for (dev_id, physport)
                                    in host_dev_map.get(host_name, [])]))
                host_rack_networks = {}
                for dev in dev_list:
                    host_rack_networks[dev] = dev_networks.get(dev, [])
                rack_networks[host_name] = host_rack_networks

            return rack_networks

        host_dev_map, dev_host_map = _get_physnet_mappings()
        rack_networks = _get_rack_networks(
                                    host_dev_map, dev_host_map, host_state_map)

        for state_key in host_state_map.keys():
            host_state = self.host_state_map[state_key]
            (host, node) = state_key
            host_state.physnet_config = host_dev_map.get(host, [])
            host_state.rack_networks = rack_networks.get(host, [])

    def get_all_host_states(self, context):
        """Returns a list of HostStates that represents all the hosts
        the HostManager knows about. Also, each of the consumable resources
        in HostState are pre-populated and adjusted based on data in the db.
        """

        # Get resource usage across the available compute nodes:
        compute_nodes = db.compute_node_get_all(context)
        seen_nodes = set()
        for compute in compute_nodes:
            service = compute['service']
            if not service:
                LOG.warn(_("No service for compute ID %s") % compute['id'])
                continue
            host = service['host']
            node = compute.get('hypervisor_hostname')
            state_key = (host, node)
            capabilities = self.service_states.get(state_key, None)
            host_state = self.host_state_map.get(state_key)
            if host_state:
                host_state.update_capabilities(capabilities,
                                               dict(service.iteritems()))
            else:
                host_state = self.host_state_cls(host, node,
                        capabilities=capabilities,
                        service=dict(service.iteritems()))
                self.host_state_map[state_key] = host_state
            host_state.update_from_compute_node(compute)
            # update information from hosted instances
            host_state.update_from_hosted_instances(context, compute)
            seen_nodes.add(state_key)

        # remove compute nodes from host_state_map if they are not active
        dead_nodes = set(self.host_state_map.keys()) - seen_nodes
        for state_key in dead_nodes:
            host, node = state_key
            LOG.info(_("Removing dead compute node %(host)s:%(node)s "
                       "from scheduler") % {'host': host, 'node': node})
            del self.host_state_map[state_key]

        # get information from groups of hosts
        # NOTE(Xinyaun): currently for POC only.
        self._get_rack_states(context, self.host_state_map)
        self._get_aggregate_stats(context, self.host_state_map)

        return self.host_state_map.itervalues()

# Copyright (c) 2012 OpenStack Foundation
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

"""IP distance cost"""

from cinderclient import exceptions as client_exceptions
from nova import db
from nova import exception
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.volume import cinder
from nova.scheduler.solvers import costs as solvercosts

LOG = logging.getLogger(__name__)

class IpDistanceCost(solvercosts.BaseCost):
    """Evaluation of the distance between computing and volume hosts
    using IP addresses.
    """
    
    hint_name = 'same_host_volume_id'
    
    def get_cost_name(self):
        return 'IpDistanceCost'
    
    def get_cost_matrix(self,hosts,instance_uuids,request_spec,filter_properties):
        num_hosts = len(hosts)
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
        
        context = filter_properties.get('context')
        scheduler_hints = filter_properties.get('scheduler_hints')
        volume_id = scheduler_hints.get(self.hint_name, False)
        
        cost_matrix = [[0.0 for j in range(num_instances)] for i in range(num_hosts)]
        
        volume_host = None
        if volume_id is not None:
            try:
                volume = cinder.cinderclient(context).volumes.get(volume_id)
                volume_host = getattr(volume, 'os-vol-host-attr:host', None)
                volume_host_ip = self._get_ip(context,volume_host)
                LOG.debug(_('Volume host is: %s') %volume_host)
                LOG.debug(_('Host ip of volume is: %s') %volume_host_ip)
            except client_exceptions.NotFound:
                LOG.warning('volume with provided id ("%s") was not found', volume_id)
        
        if volume_host is not None:
            for i in range(num_hosts):
                host_state = hosts[i]
                host_ip = host_state.host_ip
                distance = self._get_ip_distance(host_ip,volume_host_ip)
                cost_matrix[i] = [distance for j in range(num_instances)]
                LOG.debug(_('Ips: %s %s' %(host_ip,volume_host_ip)))
                LOG.debug(_('Distance between %(host1)s and %(host2)s equals: %(distanceVal)d'), \
                        {'host1':host_state.host,'host2':volume_host,'distanceVal':distance})
        
        return cost_matrix
    
    def _get_ip(self,context,host_name):
        compute_nodes = db.compute_node_get_all(context)
        #ip = None
        for node in compute_nodes:
            if node.get('hypervisor_hostname') == host_name:
                ip = node.get('host_ip')
        return ip
    
    def _get_ip_distance(self,ip_1,ip_2):
        ip_1 = ip_1.split('.')
        ip_2 = ip_2.split('.')
        ip_distance = abs((((int(ip_1[0])-int(ip_2[0]))*256-(int(ip_1[1])-int(ip_2[1])))*256-(int(ip_1[2])-int(ip_2[2])))*256-(int(ip_1[3])-int(ip_2[3])))
        return ip_distance
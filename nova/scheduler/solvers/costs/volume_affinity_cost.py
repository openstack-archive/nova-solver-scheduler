# Copyright (c) 2014 Cisco Systems Inc.
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

"""Volume affinity cost."""

from cinderclient import exceptions as client_exceptions
from nova import exception
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
import nova.volume.cinder as volumecinder
from nova.scheduler.solvers import costs as solvercosts

LOG = logging.getLogger(__name__)

class VolumeAffinityCost(solvercosts.BaseCost):
    """The cost is 0 for same-as-volume host and 1 otherwise."""
    
    hint_name = 'same_host_volume_id'
    
    def get_cost_matrix(self,hosts,instance_uuids,request_spec,filter_properties):
        num_hosts = len(hosts)
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)
        
        context = filter_properties.get('context')
        scheduler_hints = filter_properties.get('scheduler_hints')
        volume_id = scheduler_hints.get(self.hint_name, False)
        LOG.debug(_("volume id: %s") %volume_id)
        volume_host = None
        if volume_id is not None:
            try:
                volume = volumecinder.cinderclient(context).volumes.get(volume_id)
                volume_host = getattr(volume, 'os-vol-host-attr:host', None)
                LOG.debug(_("volume host: %s") %volume_host)
            except client_exceptions.NotFound:
                LOG.warning('volume with provided id ("%s") was not found', volume_id)
        
        cost_matrix = [[1.0 for j in range(num_instances)] for i in range(num_hosts)]
        if volume_host is not None:
            for i in range(num_hosts):
                host_state = hosts[i]
                if host_state.host == volume_host:
                    cost_matrix[i] = [0.0 for j in range(num_instances)]
                LOG.debug(_("this host %(host1)s " "volume host %(host2)s"),{"host1":host_state.host,"host2":volume_host})
        
        return cost_matrix
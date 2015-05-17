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

from nova.scheduler.filters import image_props_filter
from nova_solverscheduler.scheduler.solvers import constraints


class ImagePropertiesConstraint(constraints.BaseFilterConstraint):
    """Select compute nodes that satisfy instance image properties.

    The ImagePropertiesConstraint selects compute nodes that satisfy
    any architecture, hypervisor type, or virtual machine mode properties
    specified on the instance's image properties. Image properties are
    contained in the image dictionary in the request_spec.
    """
    host_filter_cls = image_props_filter.ImagePropertiesFilter

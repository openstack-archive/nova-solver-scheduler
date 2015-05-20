# Copyright (c) 2014 Cisco Systems, Inc.
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

from nova import exception
from nova.i18n import _


class SolverFailed(exception.NovaException):
    msg_fmt = _("Scheduler solver failed to find a solution. %(reason)s")


class SchedulerSolverCostNotFound(exception.NovaException):
    msg_fmt = _("Scheduler solver cost cannot be found: %(cost_name)s")


class SchedulerSolverConstraintNotFound(exception.NovaException):
    msg_fmt = _("Scheduler solver constraint cannot be found: "
                "%(constraint_name)s")

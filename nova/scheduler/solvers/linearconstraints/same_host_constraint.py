from oslo.config import cfg

from nova.compute import api as compute
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler.solvers import linearconstraints

LOG = logging.getLogger(__name__)

class SameHostConstraint(linearconstraints.AffinityConstraint):
    """Force to select hosts which are same as a set of given instances'."""

    # The linear constraint should be formed as:
    # coeff_matrix * var_matrix' (operator) constant_vector
    # where (operator) is ==, >, >=, <, <=, !=, etc.
    # For convenience, the constant_vector is merged into left-hand-side,
    # thus the right-hand-side is always 0.

    def get_coefficient_vectors(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        # Coefficients are 0 for same hosts and 1 for different hosts.
        context = filter_properties['context']
        scheduler_hints = filter_properties.get('scheduler_hints', {})
        affinity_uuids = scheduler_hints.get('same_host', [])
        if isinstance(affinity_uuids, basestring):
            affinity_uuids = [affinity_uuids]
        coefficient_vectors = []
        for host in hosts:
            if affinity_uuids:
                if self.compute_api.get_all(context,
                        {'host':host.host,
                        'uuid':affinity_uuids,
                        'deleted':False}):
                    coefficient_vectors.append([0 for j in range(self.num_instances)])
                else:
                    coefficient_vectors.append([1 for j in range(self.num_instances)])
            else:
                coefficient_vectors.append([0 for j in range(self.num_instances)])
        return coefficient_vectors

    def get_variable_vectors(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        # The variable_vectors[i,j] denotes the relationship between host[i] and instance[j].
        variable_vectors = []
        variable_vectors = [[variables[i][j] for j in range(self.num_instances)] for i in range(self.num_hosts)]
        return variable_vectors

    def get_operations(self,variables,hosts,instance_uuids,request_spec,filter_properties):
        # Operations are '=='.
        operations = [(lambda x: x==0) for i in range(self.num_hosts)]
        return operations

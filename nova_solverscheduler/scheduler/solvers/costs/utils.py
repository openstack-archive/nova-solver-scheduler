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

"""Utility methods for scheduler solver costs."""


def normalize_cost_matrix(cost_matrix):
    """This is a special normalization method for cost matrix, it
    preserves the linear relationships among current host states (first
    column of the matrix) while scaling their maximum absolute value to 1.
    Notice that by this method, the matrix is not scaled to a fixed range.
    """
    normalized_matrix = cost_matrix

    if not cost_matrix:
        return normalized_matrix

    first_column = [row[0] for row in cost_matrix]
    maxval = max(first_column)
    minval = min(first_column)
    maxabs = max(abs(maxval), abs(minval))

    if maxabs == 0:
        return normalized_matrix

    scale_factor = 1.0 / maxabs
    for i in xrange(len(cost_matrix)):
        for j in xrange(len(cost_matrix[i])):
            normalized_matrix[i][j] = cost_matrix[i][j] * scale_factor

    return normalized_matrix

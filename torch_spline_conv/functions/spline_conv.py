import torch
from torch.autograd import Variable as Var

from .degree import node_degree
from .utils import spline_weighting


def spline_conv(x,
                edge_index,
                pseudo,
                weight,
                kernel_size,
                is_open_spline,
                root_weight=None,
                degree=1,
                bias=None):

    n = x.size(0)

    # Convolve over each node.
    output = _spline_conv(x, edge_index, pseudo, weight, kernel_size,
                          is_open_spline, degree)

    # Normalize output by node degree.
    degree = x.new() if torch.is_tensor(x) else x.data.new()
    degree = node_degree(edge_index, n, out=degree).unsqueeze(-1).clamp_(min=1)
    output /= degree if torch.is_tensor(x) else Var(degree)

    # Weight root node separately (if wished).
    if root_weight is not None:
        output += torch.mm(x, root_weight)

    # Add bias (if wished).
    if bias is not None:
        output += bias

    return output


def _spline_conv(x, edge_index, pseudo, weight, kernel_size, is_open_spline,
                 degree):

    n, e, m_out = x.size(0), edge_index.size(1), weight.size(2)

    x = x.unsqueeze(-1) if x.dim() == 1 else x

    # Weight gathered features based on B-spline bases and trainable weights.
    output = spline_weighting(x[edge_index[1]], pseudo, weight, kernel_size,
                              is_open_spline, degree)

    # Perform the real convolution => Convert e x m_out to n x m_out features.
    row = edge_index[0].unsqueeze(-1).expand(e, m_out)
    row = row if torch.is_tensor(x) else Var(row)
    zero = x.new(n, m_out) if torch.is_tensor(x) else Var(x.data.new(n, m_out))
    output = zero.fill_(0).scatter_add_(0, row, output)

    return output

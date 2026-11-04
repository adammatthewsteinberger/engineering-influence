"""Fast approximate Gaussian blur."""

from typing import Any

import numpy as np
from numpy.typing import NDArray


class BoxBlur:
    """Three separable box blurs, edge-clamped."""

    def apply(self, a: NDArray[Any], sigma: float) -> NDArray[Any]:
        """Blur `a` by roughly `sigma` pixels; below 0.5 the input is returned unchanged."""
        if sigma < 0.5:
            return a
        r = max(1, round(sigma * 1.0))
        out = a.astype(np.float32)
        for axis in (0, 1):
            for _ in range(3):
                pad = [(0, 0)] * out.ndim
                pad[axis] = (r + 1, r)
                c = np.cumsum(np.pad(out, pad, mode="edge"), axis=axis, dtype=np.float64)
                n = out.shape[axis]
                hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
                lo = np.take(c, np.arange(0, n), axis=axis)
                out = ((hi - lo) / (2 * r + 1)).astype(np.float32)
        return out

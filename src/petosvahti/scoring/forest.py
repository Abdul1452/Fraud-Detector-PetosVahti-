"""Vectorised Isolation Forest inference.

scikit-learn's `IsolationForest.score_samples` loops over trees in Python and
costs ~30 ms for a single row: a third of the p99 < 100 ms budget gone on one
call. `CompiledForest` flattens every tree into shared arrays and walks all
trees at once, one numpy step per level (depth ≤ ~10), which brings a single
prediction to well under a millisecond. Scores match scikit-learn exactly
(see tests/test_model.py).
"""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from sklearn.ensemble import IsolationForest

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.intp]

EULER_GAMMA = 0.5772156649015329
_CHUNK = 4096


def average_path_length(n: npt.ArrayLike) -> FloatArray:
    """c(n): expected path length of an unsuccessful BST search (Liu et al. 2008)."""
    n = np.asarray(n, dtype=np.float64)
    out = np.zeros_like(n)
    out[n == 2] = 1.0
    big = n > 2
    out[big] = 2.0 * (np.log(n[big] - 1.0) + EULER_GAMMA) - 2.0 * (n[big] - 1.0) / n[big]
    return out


@dataclass(frozen=True)
class CompiledForest:
    left: IntArray  # global child index; leaves point to themselves
    right: IntArray
    feature: IntArray  # global feature index (bagging feature subsets resolved)
    threshold: FloatArray
    leaf_value: FloatArray  # depth + c(n_samples) at leaves, 0 elsewhere
    roots: IntArray
    depth: int
    normaliser: float  # n_trees * c(max_samples)

    @classmethod
    def from_sklearn(cls, forest: IsolationForest) -> "CompiledForest":
        lefts, rights, feats, thresholds, values, roots = [], [], [], [], [], []
        offset = 0
        max_depth = 0
        for estimator, features in zip(forest.estimators_, forest.estimators_features_, strict=True):  # fmt: skip
            tree = estimator.tree_
            n = int(tree.node_count)
            left = np.asarray(tree.children_left, dtype=np.intp)
            right = np.asarray(tree.children_right, dtype=np.intp)
            leaf = left == -1
            depth = np.zeros(n)
            for node in range(n):  # children always have larger ids than their parent
                if not leaf[node]:
                    depth[left[node]] = depth[right[node]] = depth[node] + 1
            own = np.arange(n, dtype=np.intp)
            lefts.append(np.where(leaf, own, left) + offset)
            rights.append(np.where(leaf, own, right) + offset)
            local_feature = np.where(leaf, 0, np.asarray(tree.feature, dtype=np.intp))
            feats.append(np.asarray(features, dtype=np.intp)[local_feature])
            thresholds.append(np.asarray(tree.threshold, dtype=np.float64))
            n_samples = np.asarray(tree.n_node_samples, dtype=np.float64)
            values.append(np.where(leaf, depth + average_path_length(n_samples), 0.0))
            roots.append(offset)
            offset += n
            max_depth = max(max_depth, int(tree.max_depth))
        return cls(
            left=np.concatenate(lefts),
            right=np.concatenate(rights),
            feature=np.concatenate(feats),
            threshold=np.concatenate(thresholds),
            leaf_value=np.concatenate(values),
            roots=np.asarray(roots, dtype=np.intp),
            depth=max_depth,
            normaliser=float(len(roots) * average_path_length([forest.max_samples_])[0]),
        )

    def score(self, x: FloatArray) -> FloatArray:
        """Anomaly score in (0, 1]; equals `-IsolationForest.score_samples(x)`."""
        # Trees were fitted on float32 copies of the data; compare on the same grid.
        x = np.asarray(x, dtype=np.float32).astype(np.float64)
        out = np.empty(x.shape[0], dtype=np.float64)
        for start in range(0, x.shape[0], _CHUNK):
            chunk = x[start : start + _CHUNK]
            rows = np.arange(chunk.shape[0])[:, None]
            node = np.broadcast_to(self.roots, (chunk.shape[0], self.roots.size)).copy()
            for _ in range(self.depth):
                go_left = chunk[rows, self.feature[node]] <= self.threshold[node]
                node = np.where(go_left, self.left[node], self.right[node])
            path = self.leaf_value[node].sum(axis=1)
            out[start : start + chunk.shape[0]] = 2.0 ** (-path / self.normaliser)
        return out

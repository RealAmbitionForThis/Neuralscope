"""UMAP + clustering for SAE feature maps.

Heavy compute (UMAP on 16K-65K features can take minutes); call from a
worker thread and stream progress over WebSocket.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def compute_feature_map(
    decoder_weights: np.ndarray,
    n_clusters: int = 50,
    n_neighbors: int = 30,
    min_dist: float = 0.1,
    subsample: Optional[int] = None,
    random_state: int = 42,
) -> dict:
    """Project SAE features to 2D via UMAP and assign cluster labels.

    Returns:
        {
          "coordinates": [[x, y], ...],
          "cluster_ids": [int, ...],
          "n_features": int,
          "subsampled": bool,
        }
    """
    try:
        import umap
    except ImportError as exc:
        raise RuntimeError(
            "umap-learn is not installed. Add it to backend/requirements.txt."
        ) from exc

    try:
        from sklearn.cluster import AgglomerativeClustering
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn is not installed."
        ) from exc

    n_features = decoder_weights.shape[0]
    subsampled = False

    if subsample and n_features > subsample:
        rng = np.random.default_rng(random_state)
        sample_idx = rng.choice(n_features, size=subsample, replace=False)
        sample_idx.sort()
        data = decoder_weights[sample_idx]
        subsampled = True
        feature_indices = sample_idx.tolist()
    else:
        data = decoder_weights
        feature_indices = list(range(n_features))

    logger.info("computing UMAP on %d features", data.shape[0])
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric="cosine",
        random_state=random_state,
    )
    embedding = reducer.fit_transform(data)

    logger.info("clustering %d features into %d groups", data.shape[0], n_clusters)
    safe_clusters = min(n_clusters, max(2, data.shape[0] // 2))
    clustering = AgglomerativeClustering(
        n_clusters=safe_clusters,
        metric="cosine",
        linkage="average",
    )
    cluster_labels = clustering.fit_predict(data)

    return {
        "coordinates": embedding.tolist(),
        "cluster_ids": cluster_labels.tolist(),
        "feature_indices": feature_indices,
        "n_features": int(data.shape[0]),
        "subsampled": subsampled,
        "n_clusters": int(safe_clusters),
    }

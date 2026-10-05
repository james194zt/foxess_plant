"""Performance reporting — panel temperature model, clipping, financial rollups."""

from .clipping import compute_clipping_loss_kw
from .financial import accumulate_bucket_financials, bucket_financials_gbp
from .panel_temp import plant_panel_temp_c
from .sample import collect_performance_sample
from .store import PerformanceStore

__all__ = [
    "PerformanceStore",
    "accumulate_bucket_financials",
    "bucket_financials_gbp",
    "collect_performance_sample",
    "compute_clipping_loss_kw",
    "plant_panel_temp_c",
]

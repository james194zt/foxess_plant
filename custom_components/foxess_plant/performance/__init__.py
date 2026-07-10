"""Performance reporting — virtual panel temp, clipping, financial rollups."""

from .virtual_panel_temp import compute_virtual_panel_temp_c
from .clipping import compute_clipping_loss_kw
from .financial import accumulate_bucket_financials, bucket_financials_gbp
from .sample import collect_performance_sample
from .store import PerformanceStore

__all__ = [
    "PerformanceStore",
    "accumulate_bucket_financials",
    "bucket_financials_gbp",
    "collect_performance_sample",
    "compute_clipping_loss_kw",
    "compute_virtual_panel_temp_c",
]

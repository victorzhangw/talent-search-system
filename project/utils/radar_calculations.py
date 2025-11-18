import math
from typing import Dict, List, Optional

try:
    from django.conf import settings  # type: ignore
except Exception:  # pragma: no cover - fallback when Django settings not configured
    settings = None

DEFAULT_SOFTMAX_TAU = getattr(settings, 'RADAR_SOFTMAX_TAU', 8.0) if settings else 8.0
DEFAULT_MIX_THRESHOLD = getattr(settings, 'RADAR_MIX_THRESHOLD', 7.0) if settings else 7.0
DEFAULT_HIGH_ALIGNMENT_THRESHOLD = getattr(settings, 'RADAR_HIGH_ALIGNMENT_THRESHOLD', 12.0) if settings else 12.0
DEFAULT_ADVANTAGE_FLOOR = getattr(settings, 'RADAR_ADVANTAGE_FLOOR', 70.0) if settings else 70.0
DEFAULT_CHALLENGE_FLOOR = getattr(settings, 'RADAR_CHALLENGE_FLOOR', 55.0) if settings else 55.0
DEFAULT_DOUBLE_ROLE_THRESHOLD = getattr(settings, 'RADAR_DOUBLE_ROLE_THRESHOLD', 1.2) if settings else 1.2
DEFAULT_TRIPLE_ROLE_THRESHOLD = getattr(settings, 'RADAR_TRIPLE_ROLE_THRESHOLD', 0.8) if settings else 0.8
DEFAULT_ROLE_INDEX_MEAN = getattr(settings, 'RADAR_ROLE_INDEX_MEAN', None) if settings else None
DEFAULT_ROLE_INDEX_STD = getattr(settings, 'RADAR_ROLE_INDEX_STD', None) if settings else None


def _standard_normal_cdf(value: float) -> float:
    """Return the CDF of the standard normal distribution."""
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def compute_role_based_scores(
    role_inputs: Dict[str, Dict[str, float]],
    show_mixed_role: bool,
    *,
    tau: float = DEFAULT_SOFTMAX_TAU,
    mix_threshold: float = DEFAULT_MIX_THRESHOLD,
    high_alignment_threshold: float = DEFAULT_HIGH_ALIGNMENT_THRESHOLD,
    advantage_floor: float = DEFAULT_ADVANTAGE_FLOOR,
    challenge_floor: float = DEFAULT_CHALLENGE_FLOOR,
    double_role_threshold: float = DEFAULT_DOUBLE_ROLE_THRESHOLD,
    triple_role_threshold: float = DEFAULT_TRIPLE_ROLE_THRESHOLD,
    role_index_mean: Optional[float] = DEFAULT_ROLE_INDEX_MEAN,
    role_index_std: Optional[float] = DEFAULT_ROLE_INDEX_STD,
) -> Dict[str, object]:
    """
    Compute role-based radar metrics from raw category scores.

    The output dict contains:
      - raw_scores: weighted raw score per role
      - max_scores: maximum possible score per role
      - role_index: 0-100 index per role
      - contrast_index: contrast index per role (0-100)
      - z_scores: z-value per role
      - softmax_share: softmax ratio per role (0-1)
      - softmax_share_pct: softmax ratio in percentage (0-100)
      - advantage_roles: roles with index >= advantage_floor
      - challenge_roles: roles with index <= challenge_floor
      - mixed_roles: list of role names selected as a mixed role suggestion
      - rankings: ordered list of role names from highest to lowest contrast index
    """
    if not role_inputs:
        return {
            "raw_scores": {},
            "max_scores": {},
            "role_index": {},
            "contrast_index": {},
            "z_scores": {},
            "softmax_share": {},
            "softmax_share_pct": {},
            "advantage_roles": [],
            "challenge_roles": [],
            "mixed_roles": None,
            "rankings": [],
        }

    raw_scores: Dict[str, float] = {}
    max_scores: Dict[str, float] = {}
    role_index: Dict[str, float] = {}
    weight_sums: Dict[str, float] = {}

    for name, payload in role_inputs.items():
        raw_scores[name] = float(payload.get("raw_score", 0.0) or 0.0)
        max_scores[name] = float(payload.get("max_score", 0.0) or 0.0)
        role_value = float(payload.get("role_index", 0.0) or 0.0)
        role_index[name] = max(0.0, min(100.0, role_value))
        weight_sums[name] = float(payload.get("weight_sum", 0.0) or 0.0)

    values = list(role_index.values())
    if role_index_mean is None:
        mean = sum(values) / len(values) if values else 0.0
    else:
        mean = role_index_mean

    if role_index_std is None or role_index_std <= 0:
        if values and len(values) > 1:
            variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
            stdev = math.sqrt(variance)
        else:
            stdev = 0.0
    else:
        stdev = role_index_std

    z_scores: Dict[str, float] = {}
    contrast_index: Dict[str, float] = {}

    for name, value in role_index.items():
        z = 0.0 if stdev == 0 else (value - mean) / stdev
        index = 100.0 * _standard_normal_cdf(z)
        z_scores[name] = z
        contrast_index[name] = max(0.0, min(100.0, index))

    # Softmax share calculation (always compute; caller can ignore if not needed)
    if tau is None or tau <= 0:
        tau = DEFAULT_SOFTMAX_TAU

    if role_index:
        max_index = max(role_index.values())
        denominator = 0.0
        exp_map: Dict[str, float] = {}
        for name, index in role_index.items():
            # Numerical stability: subtract the max value from the exponent argument.
            exponent = (index - max_index) / tau if tau else 0.0
            exp_value = math.exp(exponent)
            exp_map[name] = exp_value
            denominator += exp_value
    else:
        denominator = 1.0
        exp_map = {}

    softmax_share: Dict[str, float] = {}
    softmax_share_pct: Dict[str, float] = {}
    if denominator > 0:
        for name, exp_value in exp_map.items():
            share = exp_value / denominator
            softmax_share[name] = share
            softmax_share_pct[name] = share * 100.0
    else:
        for name in role_index:
            softmax_share[name] = 0.0
            softmax_share_pct[name] = 0.0

    advantage_roles = [
        name for name, value in role_index.items() if value >= advantage_floor
    ]
    challenge_roles = [
        name for name, value in role_index.items() if value <= challenge_floor
    ]

    sorted_roles: List[str] = sorted(
        contrast_index.keys(),
        key=lambda role: (contrast_index[role], softmax_share.get(role, 0.0)),
        reverse=True,
    )

    mixed_roles: Optional[List[str]] = None
    if show_mixed_role and len(sorted_roles) >= 2:
        top1, top2 = sorted_roles[0], sorted_roles[1]
        idx1 = role_index.get(top1, 0.0)
        idx2 = role_index.get(top2, 0.0)
        diff12 = abs(idx1 - idx2)

        if diff12 < high_alignment_threshold:
            share1 = softmax_share.get(top1, 0.0)
            share2 = softmax_share.get(top2, 0.0)
            ratio12 = share1 / share2 if share2 > 0 else float('inf')

            if diff12 <= mix_threshold and ratio12 <= double_role_threshold:
                mixed_roles = [top1, top2]

                if len(sorted_roles) >= 3:
                    top3 = sorted_roles[2]
                    idx3 = role_index.get(top3, 0.0)
                    diff13 = abs(idx1 - idx3)
                    share3 = softmax_share.get(top3, 0.0)
                    ratio23 = share3 / share2 if share2 > 0 else 0.0

                    if diff13 <= mix_threshold and ratio23 >= triple_role_threshold:
                        mixed_roles.append(top3)
        # 如果超過高度吻合閾值，則保持單一角色（mixed_roles = None）

    return {
        "raw_scores": raw_scores,
        "max_scores": max_scores,
        "weight_sums": weight_sums,
        "role_index": role_index,
        "contrast_index": contrast_index,
        "z_scores": z_scores,
        "softmax_share": softmax_share,
        "softmax_share_pct": softmax_share_pct,
        "advantage_roles": advantage_roles,
        "challenge_roles": challenge_roles,
        "mixed_roles": mixed_roles,
        "rankings": sorted_roles,
    }

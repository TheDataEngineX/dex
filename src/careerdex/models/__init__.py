"""ML Models for CareerDEX.

Model implementations live in ``careerdex.phases.phase4_ml_models``:

- ``ResumeJobMatcher`` — embedding + weighted scoring
- ``SalaryPredictor`` — XGBoost-style salary range prediction
- ``SkillGapAnalyzer`` — collaborative-filtering skill recommendations
- ``CareerPathRecommender`` — transition-graph career paths
- ``ChurnPredictor`` — logistic-regression churn risk
"""

from __future__ import annotations

__all__: list[str] = []

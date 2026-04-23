"""ROI Calculator — Transformation Return on Investment modelling.

Part of the CAITE Sovereign Multimedia Transformation Engine.
Provides financial modelling for the four-phase transformation framework,
calculating ROI, payback period, and value driver decomposition.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain Types
# ---------------------------------------------------------------------------

@dataclass
class ValueDriver:
    """A single value driver contributing to transformation ROI."""
    name: str
    category: str  # e.g. "cost_reduction", "revenue_growth", "risk_mitigation"
    annual_impact_eur: float
    change_percentage: float  # e.g. 0.35 for 35% improvement
    confidence: float = 0.8  # 0.0–1.0 confidence in the estimate
    notes: str = ""

    def risk_adjusted_impact(self) -> float:
        """Return impact weighted by confidence level."""
        return self.annual_impact_eur * self.confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "driver": self.name,
            "category": self.category,
            "impact_eur": round(self.annual_impact_eur, 2),
            "change_percentage": round(self.change_percentage, 3),
            "confidence": round(self.confidence, 3),
            "risk_adjusted_eur": round(self.risk_adjusted_impact(), 2),
            "notes": self.notes,
        }


@dataclass
class TransformationCost:
    """Cost component of the transformation investment."""
    name: str
    phase: int  # 1–4
    amount_eur: float
    recurring: bool = False  # one-off vs annual
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "phase": self.phase,
            "amount_eur": round(self.amount_eur, 2),
            "recurring": self.recurring,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# ROI Calculator
# ---------------------------------------------------------------------------

class ROICalculator:
    """Financial model for sovereign multimedia transformation ROI.

    Uses the value driver framework from the transformation blueprint:
    - Content monetisation velocity
    - Churn reduction
    - Production cost reduction
    - Compliance cost reduction
    - New revenue streams
    """

    def __init__(self) -> None:
        self._costs: list[TransformationCost] = []
        self._value_drivers: list[ValueDriver] = []
        log.info("ROICalculator initialised")

    def add_cost(self, cost: TransformationCost) -> None:
        """Add a cost component to the model."""
        self._costs.append(cost)
        log.info("Added cost: %s (€%.0f, phase %d)", cost.name, cost.amount_eur, cost.phase)

    def add_value_driver(self, driver: ValueDriver) -> None:
        """Add a value driver to the model."""
        self._value_drivers.append(driver)
        log.info("Added value driver: %s (€%.0f/yr)", driver.name, driver.annual_impact_eur)

    def total_investment(self, years: int = 3) -> float:
        """Calculate total investment over a period.

        Args:
            years: Investment horizon in years.

        Returns:
            Total investment in EUR.
        """
        one_off = sum(c.amount_eur for c in self._costs if not c.recurring)
        annual = sum(c.amount_eur for c in self._costs if c.recurring)
        return one_off + (annual * years)

    def annual_value(self, risk_adjusted: bool = True) -> float:
        """Calculate total annual value from all drivers.

        Args:
            risk_adjusted: Whether to weight by confidence.

        Returns:
            Total annual value in EUR.
        """
        if risk_adjusted:
            return sum(d.risk_adjusted_impact() for d in self._value_drivers)
        return sum(d.annual_impact_eur for d in self._value_drivers)

    def roi_percentage(self, years: int = 3, risk_adjusted: bool = True) -> float:
        """Calculate ROI percentage over a period.

        Args:
            years: Investment horizon.
            risk_adjusted: Whether to weight value by confidence.

        Returns:
            ROI as a percentage (e.g. 150.0 for 150% ROI).
        """
        investment = self.total_investment(years)
        if investment == 0:
            return 0.0
        total_value = self.annual_value(risk_adjusted) * years
        return ((total_value - investment) / investment) * 100

    def payback_months(self, risk_adjusted: bool = True) -> float:
        """Calculate payback period in months.

        Returns:
            Months until investment is recovered. Returns -1 if value is zero.
        """
        annual = self.annual_value(risk_adjusted)
        if annual <= 0:
            return -1.0
        investment = self.total_investment(years=1)
        return (investment / annual) * 12

    def generate_report(self, years: int = 3) -> dict[str, Any]:
        """Generate a comprehensive ROI report.

        Args:
            years: Investment horizon.

        Returns:
            Report dict compatible with the dashboard schema.
        """
        report = {
            "summary": {
                "total_investment_eur": round(self.total_investment(years), 2),
                "annual_value_eur": round(self.annual_value(risk_adjusted=True), 2),
                "annual_value_gross_eur": round(self.annual_value(risk_adjusted=False), 2),
                "roi_percentage": round(self.roi_percentage(years), 1),
                "payback_months": round(self.payback_months(), 1),
                "horizon_years": years,
            },
            "costs": [c.to_dict() for c in self._costs],
            "costs_by_phase": self._costs_by_phase(),
            "value_drivers": [d.to_dict() for d in self._value_drivers],
            "value_by_category": self._value_by_category(),
        }
        log.info("ROI report generated: %.1f%% over %d years", report["summary"]["roi_percentage"], years)
        return report

    def load_default_model(
        self,
        annual_revenue_eur: float = 10_000_000,
        employee_count: int = 200,
    ) -> None:
        """Load the default CAITE transformation model with typical ranges.

        Uses the value driver ranges from the transformation blueprint.

        Args:
            annual_revenue_eur: Organisation's annual revenue.
            employee_count: Total headcount.
        """
        # --- Costs ---
        self.add_cost(TransformationCost(
            name="Sovereignty architecture assessment", phase=1,
            amount_eur=50_000))
        self.add_cost(TransformationCost(
            name="Semantic Graph infrastructure", phase=2,
            amount_eur=120_000))
        self.add_cost(TransformationCost(
            name="Immersive pilot development", phase=3,
            amount_eur=180_000))
        self.add_cost(TransformationCost(
            name="Agent swarm deployment", phase=4,
            amount_eur=150_000))
        self.add_cost(TransformationCost(
            name="Sovereign infrastructure (annual)", phase=1,
            amount_eur=96_000, recurring=True))
        self.add_cost(TransformationCost(
            name="Operations & monitoring (annual)", phase=4,
            amount_eur=72_000, recurring=True))

        # --- Value Drivers (mid-range estimates from blueprint) ---
        self.add_value_driver(ValueDriver(
            name="Content monetisation velocity",
            category="revenue_growth",
            annual_impact_eur=annual_revenue_eur * 0.045,
            change_percentage=0.45, confidence=0.7))
        self.add_value_driver(ValueDriver(
            name="Churn reduction",
            category="revenue_growth",
            annual_impact_eur=annual_revenue_eur * 0.02,
            change_percentage=0.20, confidence=0.75))
        self.add_value_driver(ValueDriver(
            name="Production cost reduction",
            category="cost_reduction",
            annual_impact_eur=employee_count * 2_500,
            change_percentage=0.30, confidence=0.8))
        self.add_value_driver(ValueDriver(
            name="Compliance cost reduction",
            category="cost_reduction",
            annual_impact_eur=employee_count * 1_200,
            change_percentage=0.55, confidence=0.85))

    # -- internal helpers --------------------------------------------------

    def _costs_by_phase(self) -> dict[int, float]:
        result: dict[int, float] = {}
        for c in self._costs:
            result[c.phase] = result.get(c.phase, 0) + c.amount_eur
        return result

    def _value_by_category(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for d in self._value_drivers:
            result[d.category] = result.get(d.category, 0) + d.risk_adjusted_impact()
        return result

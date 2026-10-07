#!/usr/bin/env python3
"""Check wholly synthetic arithmetic only. No files, network or real data read.

Python 3.10+; standard library only. Run:
    python check_methodology_examples.py

This is not a statistical model, contract validator or forecast scoring service.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
import json
import math


def verify_examples():
    checks = 0

    def require(condition, description):
        nonlocal checks
        if not condition:
            raise AssertionError(description)
        checks += 1

    D = Decimal
    with localcontext() as context:
        context.prec = 40
        start, middle, end, years = D("2"), D("4"), D("8"), D("2")
        require(start > 0 and end > 0 and years > 0, "positive ratio scale and duration")
        ratio = end / start
        annualized = ratio.sqrt() - 1  # exactly two elapsed years in this example
        doubling_months = 12 * float(years) * math.log(2) / math.log(float(ratio))
        require(ratio == D("4"), "fourfold endpoint ratio")
        require(middle / start == end / middle == D("2"), "synthetic midpoint doubles")
        require(annualized == D("1"), "annualized fractional change")
        require(annualized * 100 == D("100"), "annualized percent change")
        require(math.isclose(doubling_months, 12, abs_tol=1e-12), "equivalent doubling months")

        old, new = Fraction(40, 100), Fraction(60, 100)
        points = (new - old) * 100
        relative = (new - old) / old
        error_reduction = ((1 - old) - (1 - new)) / (1 - old)
        require(points == 20, "percentage-point difference")
        require(relative == Fraction(1, 2), "relative score increase")
        require(error_reduction == Fraction(1, 3), "relative error reduction")
        require(points != relative * 100, "absolute and relative change differ")

        probabilities = [D("0.2"), D("0.6"), D("0.7"), D("0.9")]
        outcomes = [D("0"), D("1"), D("0"), D("1")]
        require(all(D("0") <= p <= D("1") for p in probabilities), "probability domain")
        require(all(y in {D("0"), D("1")} for y in outcomes), "binary outcomes")
        squared_errors = [(p - y) ** 2 for p, y in zip(probabilities, outcomes)]
        require(squared_errors == [D("0.04"), D("0.16"), D("0.49"), D("0.01")], "individual errors")
        total = sum(squared_errors)
        loss = total / len(probabilities)
        baseline = sum((D("0.5") - y) ** 2 for y in outcomes) / len(outcomes)
        illustrative_skill = lambda model_loss, reference_loss: None if reference_loss == 0 else 1 - model_loss / reference_loss
        skill = illustrative_skill(loss, baseline)
        require(illustrative_skill(D("0"), D("0")) is None, "zero baseline loss makes relative skill undefined")
        require(total == D("0.70"), "sum of squared errors")
        require(loss == D("0.175"), "mean Brier loss")
        require(baseline == D("0.25"), "illustrative baseline loss")
        require(skill == D("0.30"), "baseline-relative skill")
        require(skill * 100 == D("30"), "loss reduction percentage")

        return {
            "status": "passed",
            "synthetic": True,
            "checks_passed": checks,
            "scope": "Arithmetic for invented examples only; no real observations, model fit, calibration validation or public scoring.",
            "example_a": {"endpoint_ratio": str(ratio), "annualized_fractional_change": str(annualized), "annualized_percent_change": str(annualized * 100), "equivalent_doubling_months": str(round(doubling_months, 12))},
            "example_b": {"percentage_point_change": str(points), "relative_score_increase": str(relative), "relative_error_reduction": str(error_reduction), "paired_uncertainty": "not_computable_from_marginal_counts_alone"},
            "example_c": {"squared_errors": [str(x) for x in squared_errors], "sum": str(total), "mean_brier_loss": str(loss), "constant_half_baseline_loss": str(baseline), "relative_skill": str(skill), "calibration_claim": "none"}
        }


if __name__ == "__main__":
    print(json.dumps(verify_examples(), indent=2))

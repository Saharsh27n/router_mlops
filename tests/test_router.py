"""Tests for the routing policy, the cost model, and the feature contract."""

from __future__ import annotations

import pytest

from router import policy
from router.features import NUMERIC_FEATURES, TEXT_COLUMN, build_frame, numeric_features
from router.train import build_pipeline, load_split, predict_with_confidence

# ------------------------------------------------------------------ policy


@pytest.mark.parametrize("confidence", [0.0, 0.5, 1.0])
def test_complex_always_goes_expensive_regardless_of_confidence(confidence):
    assert policy.decide("complex", confidence).model == policy.EXPENSIVE


@pytest.mark.parametrize("confidence", [0.0, 0.5, 1.0])
def test_simple_always_goes_cheap_regardless_of_confidence(confidence):
    assert policy.decide("simple", confidence).model == policy.CHEAP


def test_moderate_is_the_only_class_the_threshold_applies_to():
    assert policy.decide("moderate", 0.9, threshold=0.6).model == policy.CHEAP
    assert policy.decide("moderate", 0.3, threshold=0.6).model == policy.EXPENSIVE


def test_threshold_boundary_is_inclusive():
    assert policy.decide("moderate", 0.6, threshold=0.6).model == policy.CHEAP


def test_expensive_model_really_is_more_expensive():
    """If this ever flips, every savings number in the project inverts silently."""
    assert policy.cost_usd(policy.EXPENSIVE, 1000, 1000) > policy.cost_usd(policy.CHEAP, 1000, 1000)


def test_cost_scales_linearly_with_tokens():
    single = policy.cost_usd(policy.CHEAP, 100, 100)
    assert policy.cost_usd(policy.CHEAP, 1000, 1000) == pytest.approx(single * 10)


def test_projected_costs_never_exceed_the_always_expensive_baseline():
    queries = ["short one", "a considerably longer query that asks for a lot more detail"]
    routed, baseline = policy.projected_costs(queries, ["simple", "complex"], [0.9, 0.9], 0.6)
    assert routed <= baseline


# ------------------------------------------------------------------ features


def test_build_frame_emits_exactly_the_contracted_columns():
    """The column set is the train/serve contract. Adding a feature without
    retraining would otherwise fail deep inside sklearn with an opaque error."""
    frame = build_frame(["hello world"])
    assert list(frame.columns) == [TEXT_COLUMN, *NUMERIC_FEATURES]


def test_numeric_features_are_pure_and_stateless():
    query = "Write a python function to reverse a list. Show it step by step."
    assert numeric_features(query) == numeric_features(query)


def test_numeric_features_handle_an_empty_string_without_dividing_by_zero():
    feats = numeric_features("")
    assert feats["digit_ratio"] == 0.0
    assert feats["avg_word_len"] == 0.0


def test_keyword_flags_fire_on_the_patterns_they_target():
    assert numeric_features("Write a python function to sort a list")["kw_code"] == 1.0
    assert numeric_features("Explain why the sky is blue")["kw_explain"] == 1.0
    assert numeric_features("Solve this step by step")["kw_reasoning"] == 1.0
    assert numeric_features("Pride and Prejudice")["kw_code"] == 0.0


# ------------------------------------------------------------------ model


@pytest.fixture(scope="module")
def fitted_pipeline():
    X_train, _, y_train, _ = load_split()
    # Fast slice for snappy unit test execution
    X_sub, y_sub = X_train[:60], y_train[:60]
    pipe = build_pipeline("logreg", use_numeric=True)
    pipe.fit(build_frame(X_sub), y_sub)
    return pipe


def test_predictions_are_valid_labels_with_confidences_in_range(fitted_pipeline):
    labels, confidences = predict_with_confidence(
        fitted_pipeline, ["Who painted the Mona Lisa?", "Write a function to merge two lists"]
    )
    assert len(labels) == len(confidences) == 2
    assert set(labels) <= {"simple", "moderate", "complex"}
    assert all(0.0 <= c <= 1.0 for c in confidences)


def test_linearsvc_exposes_a_confidence_despite_having_no_predict_proba():
    """The policy needs a confidence from every candidate model, so the sweep would
    be unable to compare LinearSVC at all without the softmax fallback."""
    X_train, _, y_train, _ = load_split()
    X_sub, y_sub = X_train[:60], y_train[:60]
    pipe = build_pipeline("linsvc", use_numeric=True)
    pipe.fit(build_frame(X_sub), y_sub)

    assert not hasattr(pipe, "predict_proba")
    _, confidences = predict_with_confidence(pipe, ["Who wrote Hamlet?"])
    assert 0.0 <= confidences[0] <= 1.0

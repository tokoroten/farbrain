"""Unit tests for scoring service."""

import pytest
import numpy as np

from backend.app.services.scoring import (
    NoveltyScorer,
    calculate_novelty_score,
    linear_distance_transform,
    min_distance_transform,
    exponential_distance_transform,
    percentile_distance_transform,
    top_k_distance_transform,
)


class TestLinearDistanceTransform:
    """Tests for linear_distance_transform."""

    def test_empty_similarities(self):
        """Should return 50.0 for empty array."""
        result = linear_distance_transform(np.array([]))
        assert result == 50.0

    def test_perfect_similarity(self):
        """Should return 0 for perfect similarity."""
        similarities = np.array([1.0, 1.0, 1.0])
        result = linear_distance_transform(similarities)
        assert result == 0.0

    def test_no_similarity(self):
        """Should return high score for no similarity."""
        similarities = np.array([0.0, 0.0, 0.0])
        result = linear_distance_transform(similarities)
        assert result == 50.0  # avg distance = 1.0, * 50 = 50

    def test_mixed_similarities(self):
        """Should handle mixed similarities."""
        similarities = np.array([0.9, 0.5, 0.1])
        result = linear_distance_transform(similarities)
        # distances = [0.1, 0.5, 0.9], avg = 0.5, score = 25
        assert pytest.approx(result, rel=1e-2) == 25.0


class TestMinDistanceTransform:
    """Tests for min_distance_transform."""

    def test_empty_similarities(self):
        """Should return 50.0 for empty array."""
        result = min_distance_transform(np.array([]))
        assert result == 50.0

    def test_one_very_similar(self):
        """Should return low score if one idea is very similar."""
        similarities = np.array([0.95, 0.1, 0.2])
        result = min_distance_transform(similarities)
        # min distance = 0.05, score = 2.5
        assert pytest.approx(result, rel=1e-2) == 2.5

    def test_all_dissimilar(self):
        """Should return high score if all are dissimilar."""
        similarities = np.array([0.1, 0.2, 0.15])
        result = min_distance_transform(similarities)
        # min distance = 0.8, score = 40
        assert pytest.approx(result, rel=1e-2) == 40.0


class TestExponentialDistanceTransform:
    """Tests for exponential_distance_transform."""

    def test_empty_similarities(self):
        """Should return 50.0 for empty array."""
        result = exponential_distance_transform(np.array([]))
        assert result == 50.0

    def test_beta_greater_than_one(self):
        """Beta > 1 should emphasize larger distances."""
        similarities = np.array([0.9, 0.5])
        result_linear = linear_distance_transform(similarities)
        result_exp = exponential_distance_transform(similarities, beta=2.0)

        # Exponential should give higher score due to emphasis on larger distance
        assert result_exp >= result_linear

    def test_beta_less_than_one(self):
        """Beta < 1 should dampen distances."""
        similarities = np.array([0.9, 0.1])
        result_linear = linear_distance_transform(similarities)
        result_exp = exponential_distance_transform(similarities, beta=0.5)

        # Exponential should give lower score due to dampening
        assert result_exp <= result_linear


class TestPercentileDistanceTransform:
    """Tests for percentile_distance_transform."""

    def test_empty_similarities(self):
        """Should return 50.0 for empty array."""
        result = percentile_distance_transform(np.array([]))
        assert result == 50.0

    def test_median_percentile(self):
        """50th percentile should use median distance."""
        similarities = np.array([0.9, 0.5, 0.1])
        result = percentile_distance_transform(similarities, percentile=50.0)
        # distances = [0.1, 0.5, 0.9], median = 0.5, score = 25
        assert pytest.approx(result, rel=1e-2) == 25.0

    def test_high_percentile(self):
        """High percentile should give higher scores."""
        similarities = np.array([0.9, 0.5, 0.1])
        result_50 = percentile_distance_transform(similarities, percentile=50.0)
        result_90 = percentile_distance_transform(similarities, percentile=90.0)
        assert result_90 > result_50


class TestTopKDistanceTransform:
    """Tests for top_k_distance_transform."""

    def test_empty_similarities(self):
        """Should return 50.0 for empty array."""
        result = top_k_distance_transform(np.array([]))
        assert result == 50.0

    def test_k_larger_than_array(self):
        """Should handle k larger than array size."""
        similarities = np.array([0.9, 0.5])
        result = top_k_distance_transform(similarities, k=10)
        # Should use all available distances
        expected = linear_distance_transform(similarities)
        assert pytest.approx(result, rel=1e-2) == expected

    def test_top_k_selection(self):
        """Should only consider k closest ideas."""
        similarities = np.array([0.95, 0.9, 0.5, 0.1, 0.05])
        result = top_k_distance_transform(similarities, k=2)
        # Top 2 closest: distances = [0.05, 0.1], avg = 0.075, score = 3.75
        assert pytest.approx(result, rel=1e-1) == 3.75


class TestNoveltyScorer:
    """Tests for NoveltyScorer class."""

    def test_default_transform(self):
        """Should use linear transform by default."""
        scorer = NoveltyScorer()
        new_emb = [1.0, 0.0, 0.0]
        existing_embs = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

        score = scorer.calculate_score(new_emb, existing_embs)
        assert 0 <= score <= 100

    def test_custom_transform(self):
        """Should use custom transformation function."""

        def custom_transform(similarities):
            return 99.0 if len(similarities) > 0 else 50.0

        scorer = NoveltyScorer(custom_transform)
        new_emb = [1.0, 0.0, 0.0]
        existing_embs = [[0.0, 1.0, 0.0]]

        score = scorer.calculate_score(new_emb, existing_embs)
        assert score == 99.0

    def test_set_transform(self):
        """Should allow changing transformation function."""
        scorer = NoveltyScorer(linear_distance_transform)

        def new_transform(similarities):
            return 42.0

        scorer.set_transform(new_transform)

        new_emb = [1.0, 0.0]
        existing_embs = [[0.0, 1.0]]
        score = scorer.calculate_score(new_emb, existing_embs)
        assert score == 42.0

    def test_empty_existing_embeddings(self):
        """Should handle empty existing embeddings."""
        scorer = NoveltyScorer()
        new_emb = [1.0, 0.0, 0.0]
        existing_embs = []

        score = scorer.calculate_score(new_emb, existing_embs)
        assert score == 50.0

    def test_dimension_mismatch(self):
        """Should raise error for dimension mismatch."""
        scorer = NoveltyScorer()
        new_emb = [1.0, 0.0, 0.0]  # 3-dim
        existing_embs = [[1.0, 0.0]]  # 2-dim

        with pytest.raises(ValueError, match="dimension mismatch"):
            scorer.calculate_score(new_emb, existing_embs)

    def test_numpy_array_input(self):
        """Should accept numpy arrays."""
        scorer = NoveltyScorer()
        new_emb = np.array([1.0, 0.0, 0.0])
        existing_embs = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

        score = scorer.calculate_score(new_emb, existing_embs)
        assert 0 <= score <= 100

    def test_real_embeddings(self):
        """Test with realistic embedding vectors."""
        scorer = NoveltyScorer()

        # Simulate 384-dim embeddings
        np.random.seed(42)
        new_emb = np.random.randn(384)
        new_emb = new_emb / np.linalg.norm(new_emb)  # Normalize

        existing_embs = [
            np.random.randn(384) / np.linalg.norm(np.random.randn(384))
            for _ in range(10)
        ]

        score = scorer.calculate_score(new_emb, existing_embs)
        assert 0 <= score <= 100


class TestCalculateNoveltyScore:
    """Tests for calculate_novelty_score convenience function."""

    def test_default_usage(self):
        """Should work with default parameters."""
        new_emb = [1.0, 0.0, 0.0]
        existing_embs = [[0.0, 1.0, 0.0]]

        score = calculate_novelty_score(new_emb, existing_embs)
        assert 0 <= score <= 100

    def test_custom_transform(self):
        """Should accept custom transformation function."""

        def custom_transform(similarities):
            return 88.0

        new_emb = [1.0, 0.0]
        existing_embs = [[0.0, 1.0]]

        score = calculate_novelty_score(new_emb, existing_embs, custom_transform)
        assert score == 88.0


@pytest.mark.parametrize(
    "transform_fn,expected_behavior",
    [
        (linear_distance_transform, "average distance"),
        (min_distance_transform, "minimum distance"),
        (exponential_distance_transform, "exponential emphasis"),
        (percentile_distance_transform, "percentile-based"),
        (top_k_distance_transform, "top-k average"),
    ],
)
def test_all_transforms_return_valid_scores(transform_fn, expected_behavior):
    """All transforms should return scores in valid range."""
    similarities = np.array([0.9, 0.7, 0.5, 0.3, 0.1])

    if transform_fn == exponential_distance_transform:
        score = transform_fn(similarities, beta=2.0)
    elif transform_fn == percentile_distance_transform:
        score = transform_fn(similarities, percentile=75.0)
    elif transform_fn == top_k_distance_transform:
        score = transform_fn(similarities, k=3)
    else:
        score = transform_fn(similarities)

    assert 0 <= score <= 100, f"{expected_behavior} should return score in 0-100"

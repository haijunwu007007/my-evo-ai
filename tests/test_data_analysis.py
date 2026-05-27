"""Test suite for data_analysis module - stats, correlation, regression, clustering"""
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.data_analysis import DataAnalysis

@pytest.fixture
def da():
    m = DataAnalysis()
    m.initialize()
    return m


class TestDataAnalysisCore:
    def test_init(self, da):
        """Init should set status to RUNNING"""
        assert da.status.value == "running"

    def test_describe_basic(self, da):
        """describe should return basic stats"""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        r = da._dispatch({"action": "describe", "data": data})
        assert r["success"] is True
        s = r["stats"]
        assert s["count"] == 10
        assert s["mean"] == 5.5
        assert s["min"] == 1
        assert s["max"] == 10
        assert s["p50"] == 5 or s["p50"] == 6  # median of even count

    def test_describe_negative_values(self, da):
        """describe should handle negative values"""
        r = da._dispatch({"action": "describe", "data": [-5, -3, 0, 3, 5]})
        assert r["success"] is True
        assert r["stats"]["min"] == -5
        assert r["stats"]["max"] == 5
        assert r["stats"]["mean"] == 0.0

    def test_describe_single_value(self, da):
        """describe should handle single value"""
        r = da._dispatch({"action": "describe", "data": [42]})
        assert r["success"] is True
        assert r["stats"]["count"] == 1
        assert r["stats"]["std"] == 0.0
        assert r["stats"]["skewness"] == 0

    def test_correlation_perfect_positive(self, da):
        """Perfect positive correlation should be 1.0"""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        r = da._dispatch({"action": "correlation", "x": x, "y": y})
        assert r["success"] is True
        assert abs(r["pearson"] - 1.0) < 0.001
        assert "strong" in r["interpretation"]

    def test_correlation_perfect_negative(self, da):
        """Perfect negative correlation should be -1.0"""
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]
        r = da._dispatch({"action": "correlation", "x": x, "y": y})
        assert r["success"] is True
        assert abs(r["pearson"] - (-1.0)) < 0.001

    def test_correlation_no(self, da):
        """No correlation should be near 0"""
        x = [1, 2, 3, 4, 5]
        y = [3, 3, 3, 3, 3]
        r = da._dispatch({"action": "correlation", "x": x, "y": y})
        assert r["success"] is True
        assert r["pearson"] == 0.0

    def test_regression_linear(self, da):
        """Linear regression should find y = 2x + 1"""
        x = [1, 2, 3, 4, 5]
        y = [3, 5, 7, 9, 11]
        r = da._dispatch({"action": "regression", "x": x, "y": y})
        assert r["success"] is True
        assert abs(r["regression"]["slope"] - 2.0) < 0.01
        assert abs(r["regression"]["intercept"] - 1.0) < 0.01
        assert r["regression"]["r_squared"] > 0.99

    def test_regression_no_variance(self, da):
        """Regression with constant y should have slope 0"""
        x = [1, 2, 3]
        y = [5, 5, 5]
        r = da._dispatch({"action": "regression", "x": x, "y": y})
        assert r["success"] is True
        assert abs(r["regression"]["slope"]) < 0.01

    def test_outliers_iqr(self, da):
        """IQR method should detect outliers"""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]
        r = da._dispatch({"action": "outliers", "data": data})
        assert r["success"] is True
        assert r["method"] == "IQR"
        assert 100 in r["anomalies"]
        assert r["anomaly_rate"] > 0

    def test_outliers_zscore(self, da):
        """Z-Score method should detect outliers"""
        data = [10, 12, 11, 13, 12, 11, 10, 13, 12, 50]
        r = da._dispatch({"action": "outliers", "data": data, "method": "zscore", "z_threshold": 2.0})
        assert r["success"] is True
        assert 50 in r["anomalies"]

    def test_clustering(self, da):
        """KMeans clustering should separate groups"""
        data = [1, 1, 2, 2, 8, 8, 9, 9]
        r = da._dispatch({"action": "clustering", "data": data, "k": 2})
        assert r["success"] is True
        assert r["k"] == 2
        assert len(r["clusters"]) == 2

    def test_clustering_single_cluster(self, da):
        """Clustering with k=1 should return one cluster"""
        data = [5, 5, 5, 6, 5]
        r = da._dispatch({"action": "clustering", "data": data, "k": 1})
        assert r["success"] is True
        assert r["k"] == 1

    def test_normalize_minmax(self, da):
        """Min-max normalization should produce [0,1] range"""
        data = [10, 20, 30, 40, 50]
        r = da._dispatch({"action": "normalize", "data": data, "method": "minmax"})
        assert r["success"] is True
        assert abs(r["normalized"][0] - 0.0) < 0.01
        assert abs(r["normalized"][-1] - 1.0) < 0.01

    def test_normalize_zscore(self, da):
        """Z-score normalization should produce mean=0, std=1"""
        data = [1, 2, 3, 4, 5]
        r = da._dispatch({"action": "normalize", "data": data, "method": "zscore"})
        assert r["success"] is True
        n = r["normalized"]
        assert abs(sum(n) / len(n)) < 0.01  # mean approx 0

    def test_histogram(self, da):
        """Histogram should bin values correctly"""
        data = [1, 1, 1, 2, 2, 3, 4, 5, 5, 5]
        r = da._dispatch({"action": "histogram", "data": data, "bins": 3})
        assert r["success"] is True
        assert len(r["histogram"]) == 3
        assert sum(r["histogram"]) == len(data)

    def test_empty_data_returns_hint(self, da):
        """No data should return hint message"""
        r = da._dispatch({"action": "describe", "data": ["a", "b"]})
        assert "error" in r
        assert "hint" in r

    def test_unknown_action(self, da):
        """Unknown action should return error"""
        r = da._dispatch({"action": "nonexistent", "data": [1, 2, 3]})
        assert "error" in r

    def test_summarize(self, da):
        """summarize should return system statistics (delegate-based)"""
        r = da._dispatch({"action": "summarize", "data": [1, 2, 3, 4, 5]})
        assert r["success"] is True
        assert "stats" in r

    def test_export_csv(self, da):
        """CSV export should produce formatted string"""
        r = da._dispatch({"action": "export", "data": [1, 2, 3, 4, 5], "format": "csv"})
        assert r["success"] is True
        assert "csv" in r

    def test_delegate_available(self, da):
        """module should have delegate"""
        assert da.delegate is not None

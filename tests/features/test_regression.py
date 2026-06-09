import json, pytest
from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range
from gaussian_lsp.features.regression import GoldenFixture, RegressionHarness, RegressionResult

class TestHarness:
    def test_empty(self):
        h = RegressionHarness()
        assert h.fixture_count == 0

    def test_add(self):
        h = RegressionHarness()
        h.add_fixture(GoldenFixture(name="t", input_source="test"))
        assert h.fixture_count == 1

    def test_run(self):
        h = RegressionHarness()
        h.add_fixture(GoldenFixture(name="t", input_source="test"))
        r = h.run_fixture("t")
        assert r.passed

    def test_missing(self):
        r = RegressionHarness().run_fixture("x")
        assert not r.passed

    def test_run_all(self):
        h = RegressionHarness()
        h.add_fixture(GoldenFixture(name="a", input_source="a"))
        h.add_fixture(GoldenFixture(name="b", input_source="b"))
        assert len(h.run_all()) == 2

    def test_snapshot(self):
        r = RegressionHarness().snapshot_fixture("t", "src")
        assert json.loads(r)["name"] == "t"

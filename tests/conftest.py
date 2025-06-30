"""
Pytest configuration and fixtures for parser testing.
"""
import pytest
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from _pytest.nodes import Item


@pytest.fixture
def test_data_dir() -> Path:
    """Returns the path to test data directory."""
    return Path(__file__).parent / "fire_piping"


@pytest.fixture
def sample_chunks() -> List[Dict[str, Any]]:
    """Sample chunks data for testing."""
    return [
        {"title": "Fire Piping System Overview", "start_page": 1, "end_page": 3},
        {"title": "Material Specifications", "start_page": 4, "end_page": 6},
        {"title": "Installation Requirements", "start_page": 7, "end_page": 10}
    ]


@pytest.fixture
def sample_entities() -> List[Dict[str, Any]]:
    """Sample entities data for testing."""
    return [
        {
            "id": "pipe_001",
            "type": "pipe",
            "material": "galvanized steel",
            "diameter": 1.5,
            "schedule": "40",
            "location_page": 2
        },
        {
            "id": "fitting_001", 
            "type": "fitting",
            "material": "galvanized steel",
            "diameter": 1.5,
            "schedule": "40",
            "location_page": 3
        }
    ]


def pytest_configure(config):
    """Configure pytest settings."""
    config.addinivalue_line("markers", "smoke: mark test as smoke test for CI")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "real_world: tests that run over /specs PDFs")
    config.addinivalue_line("markers", "ground_truth: tests that require ground truth .fire.json data")
    config.addinivalue_line("markers", "performance: performance benchmark tests")
    config.addinivalue_line("markers", "strict_accuracy: fail build on accuracy regressions")


results: list[dict[str, Any]] = []


def pytest_runtest_logreport(report):
    """Collect per-test timing and outcome for benchmark analytics."""
    if report.when == "call":
        results.append({
            "test": report.nodeid,
            "outcome": report.outcome,
            "duration": report.duration,
        })


def pytest_sessionfinish(session, exitstatus):
    """Write aggregated benchmark data to JSON once the test session finishes."""
    if not results:
        return
    import json
    from pathlib import Path

    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"benchmark_{timestamp}.json"
    with out_file.open("w") as f:
        json.dump({
            "total_tests": len(results),
            "passed": sum(1 for r in results if r["outcome"] == "passed"),
            "failed": sum(1 for r in results if r["outcome"] == "failed"),
            "results": results,
        }, f, indent=2)

    session.config.pluginmanager.get_plugin("terminalreporter").write_line(
        f"\nBenchmark report written to {out_file}\n"
    )


def pytest_collection_modifyitems(config, items: list[Item]):
    """If STRICT_ACCURACY=1, turn all xfail(real_world ground_truth) into normal tests."""
    if os.getenv("STRICT_ACCURACY") not in {"1", "true", "True"}:
        return
    for item in items:
        # Remove xfail markers so failures surface
        xfail_marker = item.get_closest_marker("xfail")
        if xfail_marker is not None:
            item.own_markers.remove(xfail_marker) 
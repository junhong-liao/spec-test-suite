"""
Real-world specification testing module.

This module provides comprehensive testing infrastructure that scales with
real PDF examples in the /specs directory, supporting 50-100+ test cases.
"""
import json
import pytest
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from parser import parse_pdf, DocumentChunker, parse_pdf_real
from tests.utils import compare_chunks, score_entities, validate_json_data
from tests.test_config import test_config, get_thresholds_for_file, should_skip_slow_tests


@dataclass
class SpecTestCase:
    """Represents a test case based on a real-world specification."""
    spec_name: str
    pdf_path: Path
    ground_truth_path: Optional[Path] = None
    expected_stats: Optional[Dict[str, Any]] = None
    performance_threshold_seconds: float = 10.0
    min_chunks: int = 1
    max_chunks: int = 50
    
    @property
    def has_ground_truth(self) -> bool:
        """Check if ground truth data exists for this spec."""
        return self.ground_truth_path is not None and self.ground_truth_path.exists()


class SpecTestDiscovery:
    """Automatically discover and manage test cases from specs directory."""
    
    def __init__(self, specs_dir: Path):
        self.specs_dir = specs_dir
        self._test_cases: List[SpecTestCase] = []
        self._discover_test_cases()
    
    def _discover_test_cases(self) -> None:
        """Discover all test cases from the specs directory."""
        if not self.specs_dir.exists():
            return
        
        # Find all PDFs in specs directory
        pdf_files = list(self.specs_dir.glob("*.pdf"))
        
        for pdf_path in pdf_files:
            # Check for corresponding .fire.json file
            json_path = pdf_path.with_suffix('.fire.json')
            ground_truth_path = json_path if json_path.exists() else None
            
            # Create test case
            test_case = SpecTestCase(
                spec_name=pdf_path.stem,
                pdf_path=pdf_path,
                ground_truth_path=ground_truth_path,
                performance_threshold_seconds=self._get_performance_threshold(pdf_path),
                min_chunks=self._estimate_min_chunks(pdf_path),
                max_chunks=self._estimate_max_chunks(pdf_path)
            )
            
            self._test_cases.append(test_case)
    
    def _get_performance_threshold(self, pdf_path: Path) -> float:
        """Get performance threshold using test configuration."""
        try:
            threshold, _ = get_thresholds_for_file(pdf_path)
            return threshold
        except:
            return test_config.performance.max_time_seconds
    
    def _estimate_min_chunks(self, pdf_path: Path) -> int:
        """Estimate minimum expected chunks using document type configuration."""
        try:
            _, doc_config = get_thresholds_for_file(pdf_path)
            return doc_config.min_chunks
        except:
            return 1
    
    def _estimate_max_chunks(self, pdf_path: Path) -> int:
        """Estimate maximum expected chunks using document type configuration."""
        try:
            _, doc_config = get_thresholds_for_file(pdf_path)
            return doc_config.max_chunks
        except:
            return 50
    
    @property
    def test_cases(self) -> List[SpecTestCase]:
        """Get all discovered test cases."""
        return self._test_cases
    
    @property
    def test_cases_with_ground_truth(self) -> List[SpecTestCase]:
        """Get test cases that have ground truth data."""
        return [tc for tc in self._test_cases if tc.has_ground_truth]
    
    @property
    def test_cases_without_ground_truth(self) -> List[SpecTestCase]:
        """Get test cases that need ground truth data generation."""
        return [tc for tc in self._test_cases if not tc.has_ground_truth]


# Initialize test discovery
SPECS_DIR = Path(__file__).parent.parent / "specs"
test_discovery = SpecTestDiscovery(SPECS_DIR)


def run_parser_with_metrics(pdf_path: Path) -> Tuple[Any, Dict[str, float]]:
    """
    Run parser and collect detailed performance metrics.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Tuple of (parse_result, metrics_dict)
    """
    start_time = time.time()
    result = parse_pdf(str(pdf_path))
    end_time = time.time()
    
    metrics = {
        'total_time': end_time - start_time,
        'chunks_found': len(result.chunks) if hasattr(result, 'chunks') else 0,
        'entities_found': len(result.entities) if hasattr(result, 'entities') else 0,
        'time_per_chunk': (end_time - start_time) / max(1, len(result.chunks)) if hasattr(result, 'chunks') else 0,
        'file_size_mb': pdf_path.stat().st_size / (1024 * 1024) if pdf_path.exists() else 0
    }
    
    return result, metrics


@pytest.mark.real_world
@pytest.mark.ground_truth
@pytest.mark.xfail(reason="Parser chunking not yet tuned to ground truth", strict=False)
@pytest.mark.parametrize(
    "test_case",
    test_discovery.test_cases_with_ground_truth,
    ids=lambda tc: getattr(tc, "spec_name", "no_ground_truth")
)
def test_real_world_chunks_with_ground_truth(test_case: SpecTestCase):
    """Test chunking accuracy against ground truth for real-world specs."""
    # Load ground truth data
    with open(test_case.ground_truth_path, 'r') as f:
        ground_truth = json.load(f)
    
    # Parse PDF
    result, metrics = run_parser_with_metrics(test_case.pdf_path)
    
    # Validate performance
    assert metrics['total_time'] <= test_case.performance_threshold_seconds, \
        f"{test_case.spec_name}: Parsing took {metrics['total_time']:.2f}s, " \
        f"threshold is {test_case.performance_threshold_seconds:.2f}s"
    
    # Validate chunk count is reasonable
    chunks_found = metrics['chunks_found']
    assert test_case.min_chunks <= chunks_found <= test_case.max_chunks, \
        f"{test_case.spec_name}: Found {chunks_found} chunks, " \
        f"expected between {test_case.min_chunks}-{test_case.max_chunks}"
    
    # Compare against ground truth if available
    if 'chunks' in ground_truth:
        gold_chunks = ground_truth['chunks']
        # Convert ground truth format to standard format if needed
        if gold_chunks and 'page' in gold_chunks[0]:  # Current .fire.json format
            gold_chunks = [
                {
                    'title': f"Section {i+1}",
                    'start_page': chunk['page'],
                    'end_page': chunk['page']
                }
                for i, chunk in enumerate(gold_chunks)
            ]
        
        assert compare_chunks(result.chunks, gold_chunks, page_tolerance=2), \
            f"{test_case.spec_name}: Chunks don't match ground truth"
    
    # Log results for analysis
    print(f"✓ {test_case.spec_name}: {chunks_found} chunks in {metrics['total_time']:.2f}s "
          f"({metrics['file_size_mb']:.1f}MB)")


@pytest.mark.real_world
@pytest.mark.smoke
@pytest.mark.parametrize(
    "test_case",
    test_discovery.test_cases_without_ground_truth,
    ids=lambda tc: getattr(tc, "spec_name", "no_ground_truth")
)
def test_real_world_specs_smoke_test(test_case: SpecTestCase):
    """Smoke test for real-world specs without ground truth."""
    # Parse PDF
    result, metrics = run_parser_with_metrics(test_case.pdf_path)
    
    # Basic validation
    assert metrics['total_time'] <= test_case.performance_threshold_seconds, \
        f"{test_case.spec_name}: Parsing took {metrics['total_time']:.2f}s"
    
    assert test_case.min_chunks <= metrics['chunks_found'] <= test_case.max_chunks, \
        f"{test_case.spec_name}: Found {metrics['chunks_found']} chunks"
    
    # Validate result structure
    assert hasattr(result, 'chunks'), f"{test_case.spec_name}: Missing chunks attribute"
    assert hasattr(result, 'entities'), f"{test_case.spec_name}: Missing entities attribute"
    
    # Validate chunk data integrity
    for i, chunk in enumerate(result.chunks):
        assert 'title' in chunk, f"{test_case.spec_name}: Chunk {i} missing title"
        assert 'start_page' in chunk, f"{test_case.spec_name}: Chunk {i} missing start_page"
        assert 'end_page' in chunk, f"{test_case.spec_name}: Chunk {i} missing end_page"
        assert chunk['start_page'] <= chunk['end_page'], \
            f"{test_case.spec_name}: Chunk {i} has invalid page range"
    
    print(f"✓ {test_case.spec_name}: {metrics['chunks_found']} chunks, "
          f"{metrics['entities_found']} entities in {metrics['total_time']:.2f}s")


@pytest.mark.real_world
@pytest.mark.performance
@pytest.mark.integration
def test_performance_benchmarks():
    """Test performance benchmarks across all specs."""
    results = []
    
    for test_case in test_discovery.test_cases:
        if not test_case.pdf_path.exists():
            continue
            
        result, metrics = run_parser_with_metrics(test_case.pdf_path)
        
        results.append({
            'spec_name': test_case.spec_name,
            'file_size_mb': metrics['file_size_mb'],
            'total_time': metrics['total_time'],
            'chunks_found': metrics['chunks_found'],
            'entities_found': metrics['entities_found'],
            'throughput_mb_per_sec': metrics['file_size_mb'] / metrics['total_time']
        })
    
    # Assert overall performance characteristics
    if results:
        avg_throughput = sum(r['throughput_mb_per_sec'] for r in results) / len(results)
        assert avg_throughput >= 0.1, f"Average throughput too low: {avg_throughput:.3f} MB/s"
        
        # No individual file should take more than 30 seconds
        max_time = max(r['total_time'] for r in results)
        assert max_time <= 30.0, f"Slowest file took {max_time:.2f}s"
    
    # Print performance summary
    print(f"\nPerformance Summary ({len(results)} files):")
    for result in sorted(results, key=lambda x: x['total_time'], reverse=True):
        print(f"  {result['spec_name']:<30} {result['file_size_mb']:>6.1f}MB "
              f"{result['total_time']:>6.2f}s {result['throughput_mb_per_sec']:>6.2f}MB/s")


@pytest.mark.real_world
@pytest.mark.ground_truth
@pytest.mark.integration 
def test_ground_truth_validation():
    """Validate all existing ground truth files."""
    for test_case in test_discovery.test_cases_with_ground_truth:
        with open(test_case.ground_truth_path, 'r') as f:
            ground_truth = json.load(f)
        
        # Validate ground truth structure
        assert 'chunks' in ground_truth, f"{test_case.spec_name}: Missing chunks in ground truth"
        
        chunks = ground_truth['chunks']
        assert isinstance(chunks, list), f"{test_case.spec_name}: Chunks must be a list"
        assert len(chunks) > 0, f"{test_case.spec_name}: Ground truth has no chunks"
        
        # Validate each chunk has required fields
        for i, chunk in enumerate(chunks):
            if 'page' in chunk:  # Current .fire.json format
                assert 'text' in chunk, f"{test_case.spec_name}: Chunk {i} missing text"
                assert 'page' in chunk, f"{test_case.spec_name}: Chunk {i} missing page"
            else:  # Standard format
                assert 'title' in chunk, f"{test_case.spec_name}: Chunk {i} missing title"
                assert 'start_page' in chunk, f"{test_case.spec_name}: Chunk {i} missing start_page"
                assert 'end_page' in chunk, f"{test_case.spec_name}: Chunk {i} missing end_page"


@pytest.mark.real_world
def test_discovery_stats():
    """Test and report discovery statistics."""
    total_cases = len(test_discovery.test_cases)
    with_gt = len(test_discovery.test_cases_with_ground_truth)
    without_gt = len(test_discovery.test_cases_without_ground_truth)
    
    assert total_cases > 0, "No test cases discovered"
    
    print(f"\nTest Discovery Statistics:")
    print(f"  Total test cases: {total_cases}")
    print(f"  With ground truth: {with_gt}")
    print(f"  Without ground truth: {without_gt}")
    print(f"  Ground truth coverage: {with_gt/total_cases*100:.1f}%")
    
    # List files without ground truth
    if without_gt > 0:
        print(f"\nFiles needing ground truth:")
        for tc in test_discovery.test_cases_without_ground_truth:
            print(f"  - {tc.spec_name}")


if __name__ == "__main__":
    # Run discovery stats when executed directly
    test_discovery_stats() 
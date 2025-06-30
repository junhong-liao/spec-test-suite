#!/usr/bin/env python3
"""
Comprehensive Parser Test Suite - Integrated testing for all parsers.

This test suite consolidates all parser testing functionality:
1. Legacy gold standard tests (fast regression tests)
2. Real-world PDF tests (comprehensive validation)
3. Parser interface standardization
4. Performance benchmarking
5. Ground truth validation

All tests run from a single consolidated location.
"""
import pytest
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

# Import existing test modules
from test_parser import TEST_CASES, load_test_data, time_parser_execution
from test_real_world_specs import test_discovery, run_parser_with_metrics
from test_parser_interface_fixes import (
    PageScorerWrapper, 
    SectionStitcherWrapper, 
    ProductionChunkerOptimizer
)

# Try to import the parser
try:
    from parser import parse_pdf
except ImportError:
    # Fallback if parser not available
    def parse_pdf(pdf_path):
        class MockResult:
            def __init__(self):
                self.chunks = []
                self.entities = []
        return MockResult()


@dataclass
class ParserPerformanceResults:
    """Results from comprehensive parser performance testing."""
    parser_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    average_time: float
    total_chunks: int
    total_entities: int
    grade: str
    issues: List[str]


class ComprehensiveParserTester:
    """Comprehensive testing framework for all parsers."""
    
    def __init__(self):
        self.results = {}
        self.parsers_tested = []
    
    def test_all_parsers(self) -> Dict[str, ParserPerformanceResults]:
        """Run comprehensive tests on all available parsers."""
        print("🧪 Starting Comprehensive Parser Test Suite")
        print("=" * 60)
        
        # Test standard parser
        self._test_standard_parser()
        
        # Test interface-fixed parsers
        self._test_wrapped_parsers()
        
        # Generate summary report
        self._generate_summary_report()
        
        return self.results
    
    def _test_standard_parser(self):
        """Test the standard parser with legacy and real-world tests."""
        print("\n📋 Testing Standard Parser")
        print("-" * 30)
        
        parser_name = "standard_parser"
        issues = []
        passed = 0
        failed = 0
        total_time = 0
        total_chunks = 0
        total_entities = 0
        
        # Test legacy gold standard cases
        print("  🔹 Legacy Gold Standard Tests:")
        for test_case in TEST_CASES:
            try:
                test_case_id = test_case["id"]
                test_dir = Path(__file__).parent / "fire_piping" / test_case_id
                pdf_path = test_dir / "input.pdf"
                
                if pdf_path.exists():
                    result, exec_time = time_parser_execution(str(pdf_path))
                    total_time += exec_time
                    total_chunks += len(result.chunks)
                    total_entities += len(result.entities)
                    
                    if len(result.chunks) == test_case["expected_chunks"]:
                        passed += 1
                        print(f"    ✓ {test_case_id}: {len(result.chunks)} chunks ({exec_time:.3f}s)")
                    else:
                        failed += 1
                        issue = f"{test_case_id}: Expected {test_case['expected_chunks']} chunks, got {len(result.chunks)}"
                        issues.append(issue)
                        print(f"    ✗ {issue}")
                else:
                    failed += 1
                    issue = f"{test_case_id}: PDF file not found"
                    issues.append(issue)
                    print(f"    ✗ {issue}")
                    
            except Exception as e:
                failed += 1
                issue = f"{test_case_id}: Error - {str(e)}"
                issues.append(issue)
                print(f"    ✗ {issue}")
        
        # Test real-world PDFs
        print("  🔹 Real-World PDF Tests:")
        real_world_results = self._test_real_world_pdfs()
        passed += real_world_results['passed']
        failed += real_world_results['failed']
        total_time += real_world_results['total_time']
        total_chunks += real_world_results['total_chunks']
        total_entities += real_world_results['total_entities']
        issues.extend(real_world_results['issues'])
        
        # Calculate grade
        total_tests = passed + failed
        success_rate = (passed / total_tests) if total_tests > 0 else 0
        avg_time = (total_time / total_tests) if total_tests > 0 else 0
        
        grade = self._calculate_grade(success_rate, avg_time, len(issues))
        
        self.results[parser_name] = ParserPerformanceResults(
            parser_name=parser_name,
            total_tests=total_tests,
            passed_tests=passed,
            failed_tests=failed,
            average_time=avg_time,
            total_chunks=total_chunks,
            total_entities=total_entities,
            grade=grade,
            issues=issues
        )
        
        print(f"  📊 Results: {passed}/{total_tests} passed, Grade: {grade}")
    
    def _test_real_world_pdfs(self) -> Dict[str, Any]:
        """Test real-world PDFs with current parser."""
        results = {
            'passed': 0,
            'failed': 0,
            'total_time': 0,
            'total_chunks': 0,
            'total_entities': 0,
            'issues': []
        }
        
        # Test a subset of real-world PDFs for speed
        test_pdfs = [
            "../specs/NYC_HPD_Table_of_Contents.pdf",
            "../specs/Ohio_Cincinnati_Addendum.pdf"
        ]
        
        for pdf_path in test_pdfs:
            if Path(pdf_path).exists():
                try:
                    result, metrics = run_parser_with_metrics(Path(pdf_path))
                    results['total_time'] += metrics['total_time']
                    results['total_chunks'] += metrics['chunks_found']
                    results['total_entities'] += metrics['entities_found']
                    
                    # Basic validation - should find at least 1 chunk
                    if metrics['chunks_found'] > 0:
                        results['passed'] += 1
                        print(f"    ✓ {Path(pdf_path).name}: {metrics['chunks_found']} chunks ({metrics['total_time']:.2f}s)")
                    else:
                        results['failed'] += 1
                        issue = f"{Path(pdf_path).name}: No chunks found"
                        results['issues'].append(issue)
                        print(f"    ✗ {issue}")
                        
                except Exception as e:
                    results['failed'] += 1
                    issue = f"{Path(pdf_path).name}: Error - {str(e)}"
                    results['issues'].append(issue)
                    print(f"    ✗ {issue}")
            else:
                results['failed'] += 1
                issue = f"{Path(pdf_path).name}: File not found"
                results['issues'].append(issue)
                print(f"    ✗ {issue}")
        
        return results
    
    def _test_wrapped_parsers(self):
        """Test parsers with interface fixes."""
        print("\n🔧 Testing Interface-Fixed Parsers")
        print("-" * 35)
        
        wrapped_parsers = [
            ("page_scorer_wrapped", PageScorerWrapper),
            ("section_stitcher_wrapped", SectionStitcherWrapper),
            ("production_chunker_optimized", ProductionChunkerOptimizer)
        ]
        
        for parser_name, parser_class in wrapped_parsers:
            print(f"  🔹 Testing {parser_name}:")
            
            try:
                parser_instance = parser_class()
                issues = []
                passed = 0
                failed = 0
                total_time = 0
                total_chunks = 0
                
                # Test with one PDF
                test_pdf = "../specs/NYC_HPD_Table_of_Contents.pdf"
                if Path(test_pdf).exists():
                    start_time = time.time()
                    
                    if parser_name == "production_chunker_optimized":
                        result = parser_instance.extract_fire_sections_optimized(test_pdf, timeout_seconds=5)
                    else:
                        result = parser_instance.extract_fire_sections(test_pdf)
                    
                    end_time = time.time()
                    exec_time = end_time - start_time
                    total_time += exec_time
                    
                    chunks_found = len(result.get('chunks', []))
                    total_chunks += chunks_found
                    
                    if 'error' not in result and chunks_found > 0:
                        passed += 1
                        print(f"    ✓ Found {chunks_found} chunks ({exec_time:.2f}s)")
                    else:
                        failed += 1
                        error_msg = result.get('error', 'No chunks found')
                        issue = f"{parser_name}: {error_msg}"
                        issues.append(issue)
                        print(f"    ✗ {issue}")
                else:
                    failed += 1
                    issue = f"{parser_name}: Test PDF not found"
                    issues.append(issue)
                    print(f"    ✗ {issue}")
                
                # Calculate grade for wrapped parser
                total_tests = passed + failed
                success_rate = (passed / total_tests) if total_tests > 0 else 0
                avg_time = (total_time / total_tests) if total_tests > 0 else 0
                grade = self._calculate_grade(success_rate, avg_time, len(issues))
                
                self.results[parser_name] = ParserPerformanceResults(
                    parser_name=parser_name,
                    total_tests=total_tests,
                    passed_tests=passed,
                    failed_tests=failed,
                    average_time=avg_time,
                    total_chunks=total_chunks,
                    total_entities=0,  # Wrapped parsers don't extract entities yet
                    grade=grade,
                    issues=issues
                )
                
            except Exception as e:
                print(f"    ✗ Failed to initialize {parser_name}: {e}")
                self.results[parser_name] = ParserPerformanceResults(
                    parser_name=parser_name,
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=1,
                    average_time=0,
                    total_chunks=0,
                    total_entities=0,
                    grade="F",
                    issues=[f"Initialization failed: {str(e)}"]
                )
    
    def _calculate_grade(self, success_rate: float, avg_time: float, num_issues: int) -> str:
        """Calculate letter grade based on performance metrics."""
        # Grade based on success rate, speed, and issues
        score = 0
        
        # Success rate (60% of grade)
        if success_rate >= 0.95:
            score += 60
        elif success_rate >= 0.90:
            score += 50
        elif success_rate >= 0.80:
            score += 40
        elif success_rate >= 0.70:
            score += 30
        elif success_rate >= 0.50:
            score += 20
        else:
            score += 10
        
        # Speed (30% of grade) - prefer under 5 seconds average
        if avg_time <= 1.0:
            score += 30
        elif avg_time <= 3.0:
            score += 25
        elif avg_time <= 5.0:
            score += 20
        elif avg_time <= 10.0:
            score += 15
        else:
            score += 5
        
        # Issues (10% of grade) - fewer issues is better
        if num_issues == 0:
            score += 10
        elif num_issues <= 2:
            score += 8
        elif num_issues <= 5:
            score += 5
        else:
            score += 2
        
        # Convert to letter grade
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _generate_summary_report(self):
        """Generate and display summary report."""
        print("\n📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 60)
        
        if not self.results:
            print("No test results available.")
            return
        
        # Sort by grade
        sorted_results = sorted(
            self.results.items(), 
            key=lambda x: x[1].grade
        )
        
        print(f"{'Parser':<30} {'Grade':<6} {'Pass/Total':<10} {'Avg Time':<10} {'Chunks':<8}")
        print("-" * 60)
        
        for parser_name, result in sorted_results:
            chunks_str = str(result.total_chunks)
            pass_total = f"{result.passed_tests}/{result.total_tests}"
            avg_time_str = f"{result.average_time:.2f}s"
            
            print(f"{parser_name:<30} {result.grade:<6} {pass_total:<10} {avg_time_str:<10} {chunks_str:<8}")
        
        # Show issues for failing parsers
        print("\n🔍 Issues Found:")
        for parser_name, result in sorted_results:
            if result.issues:
                print(f"\n  {parser_name}:")
                for issue in result.issues[:3]:  # Show first 3 issues
                    print(f"    • {issue}")
                if len(result.issues) > 3:
                    print(f"    ... and {len(result.issues) - 3} more issues")


# Pytest test functions
@pytest.mark.integration
@pytest.mark.comprehensive
def test_comprehensive_parser_suite():
    """Run the comprehensive parser test suite."""
    tester = ComprehensiveParserTester()
    results = tester.test_all_parsers()
    
    # Assert that at least one parser passed some tests
    total_passed = sum(r.passed_tests for r in results.values())
    assert total_passed > 0, "No parsers passed any tests"
    
    # Assert that the standard parser has reasonable performance
    if 'standard_parser' in results:
        standard_result = results['standard_parser']
        assert standard_result.grade in ['A', 'B', 'C'], f"Standard parser grade too low: {standard_result.grade}"


@pytest.mark.smoke
def test_parser_consolidation_smoke():
    """Smoke test to verify all test files are accessible from consolidated location."""
    # Verify legacy test data exists
    test_dir = Path(__file__).parent / "fire_piping" / "gold_001"
    assert test_dir.exists(), "Legacy test data not found"
    assert (test_dir / "chunks.json").exists(), "Legacy chunks.json not found"
    
    # Verify real-world specs accessible
    specs_dir = Path(__file__).parent.parent / "specs"
    pdf_files = list(specs_dir.glob("*.pdf"))
    assert len(pdf_files) > 0, "No real-world PDF specs found"
    
    print(f"✓ Found {len(pdf_files)} real-world PDFs")
    print(f"✓ Legacy test data accessible")
    print("✓ Test consolidation successful")


if __name__ == "__main__":
    # Run comprehensive test suite
    tester = ComprehensiveParserTester()
    results = tester.test_all_parsers() 
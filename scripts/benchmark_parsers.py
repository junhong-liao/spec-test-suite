#!/usr/bin/env python3
"""
Comprehensive Parser Benchmarking and Grading System

This script evaluates all available parsers across multiple dimensions:
- Performance (speed, memory usage)
- Accuracy (chunk detection, entity extraction)
- Quality (content relevance, structure detection)
- Robustness (error handling, edge cases)
"""
import sys
import time
import json
import statistics
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional, NamedTuple
from dataclasses import dataclass
import psutil
import os

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "parsers"))

@dataclass
class BenchmarkResult:
    """Results from benchmarking a single parser on a single PDF."""
    parser_name: str
    pdf_name: str
    
    # Performance metrics
    parse_time_seconds: float
    memory_peak_mb: float
    memory_delta_mb: float
    cpu_percent: float
    
    # Output metrics
    chunks_found: int
    entities_found: int
    total_text_length: int
    
    # Quality metrics
    fire_content_chunks: int
    toc_detection_score: float
    content_diversity_score: float
    
    # Error handling
    success: bool
    error_message: Optional[str] = None

@dataclass
class ParserGrade:
    """Overall grade for a parser across all tests."""
    parser_name: str
    
    # Performance grades (0-100)
    speed_grade: float
    memory_grade: float
    reliability_grade: float
    
    # Accuracy grades (0-100)
    chunk_detection_grade: float
    entity_extraction_grade: float
    content_quality_grade: float
    
    # Overall grades
    performance_grade: float
    accuracy_grade: float
    overall_grade: float
    
    # Statistics
    tests_run: int
    successful_tests: int
    avg_parse_time: float
    avg_chunks_found: float

class ParserBenchmark:
    """Main benchmarking class for testing parsers."""
    
    def __init__(self, specs_dir: Path):
        self.specs_dir = Path(specs_dir)
        self.parsers_dir = Path(__file__).parent.parent / "parsers"
        self.results: List[BenchmarkResult] = []
        self.available_parsers = self._discover_parsers()
        
    def _discover_parsers(self) -> Dict[str, Any]:
        """Discover all available parser modules."""
        parsers = {}
        
        parser_files = [
            'toc_driven_chunker.cpython-313.pyc',
            'production_chunker.cpython-313.pyc', 
            'page_scoring.cpython-313.pyc',
            'section_stitcher.cpython-313.pyc'
        ]
        
        for pyc_file in parser_files:
            module_name = pyc_file.split('.')[0]
            pyc_path = self.parsers_dir / pyc_file
            
            if pyc_path.exists():
                try:
                    spec = importlib.util.spec_from_file_location(module_name, str(pyc_path))
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)
                        
                        # Get the appropriate class
                        parser_class = None
                        if module_name == 'toc_driven_chunker':
                            parser_class = module.TOCDrivenChunker
                        elif module_name == 'production_chunker':
                            parser_class = module.ProductionSpecChunker
                        elif module_name == 'page_scoring':
                            parser_class = module.PageScorer
                        elif module_name == 'section_stitcher':
                            parser_class = module.SectionStitcher
                            
                        if parser_class:
                            parsers[module_name] = parser_class
                            print(f"✓ Discovered parser: {module_name}")
                        
                except Exception as e:
                    print(f"✗ Failed to load {module_name}: {e}")
                    
        return parsers
    
    def _measure_memory_usage(self, func, *args, **kwargs):
        """Measure memory usage during function execution."""
        process = psutil.Process()
        
        # Get initial memory
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Execute function and measure peak memory
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        end_time = time.time()
        
        # Get final memory
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            'result': result,
            'success': success,
            'error': error,
            'execution_time': end_time - start_time,
            'memory_before': memory_before,
            'memory_after': memory_after,
            'memory_delta': memory_after - memory_before,
            'memory_peak': max(memory_before, memory_after)
        }
    
    def _analyze_parser_output(self, result: Any, parser_name: str) -> Dict[str, Any]:
        """Analyze the output quality of a parser."""
        analysis = {
            'chunks_found': 0,
            'entities_found': 0,
            'total_text_length': 0,
            'fire_content_chunks': 0,
            'toc_detection_score': 0.0,
            'content_diversity_score': 0.0
        }
        
        if not result:
            return analysis
            
        # Handle different parser output formats
        if isinstance(result, dict):
            # TOC and Production chunkers
            if 'chunks' in result:
                chunks = result['chunks']
                analysis['chunks_found'] = len(chunks)
                
                fire_keywords = ['fire', 'suppression', 'sprinkler', 'piping', 'protection']
                toc_keywords = ['table', 'contents', 'section', 'division']
                
                total_text = ""
                fire_count = 0
                toc_score = 0
                
                for chunk in chunks:
                    text = chunk.get('text', '').lower()
                    total_text += text
                    
                    # Count fire protection content
                    if any(keyword in text for keyword in fire_keywords):
                        fire_count += 1
                    
                    # Score TOC detection
                    if any(keyword in text for keyword in toc_keywords):
                        toc_score += 1
                        
                analysis['total_text_length'] = len(total_text)
                analysis['fire_content_chunks'] = fire_count
                analysis['toc_detection_score'] = min(100.0, (toc_score / len(chunks)) * 100) if chunks else 0
                
                # Calculate content diversity (unique words per chunk)
                if chunks:
                    words_per_chunk = [len(set(chunk.get('text', '').split())) for chunk in chunks]
                    analysis['content_diversity_score'] = statistics.mean(words_per_chunk) if words_per_chunk else 0
                    
            # Check for other content types
            for content_type in ['primary_content', 'secondary_content']:
                if content_type in result:
                    analysis['entities_found'] += len(result[content_type])
                    
        return analysis
    
    def benchmark_parser(self, parser_name: str, pdf_path: Path) -> BenchmarkResult:
        """Benchmark a single parser on a single PDF."""
        print(f"  📊 Benchmarking {parser_name} on {pdf_path.name}...")
        
        # Initialize parser
        try:
            parser_class = self.available_parsers[parser_name]
            parser = parser_class()
        except Exception as e:
            return BenchmarkResult(
                parser_name=parser_name,
                pdf_name=pdf_path.name,
                parse_time_seconds=0,
                memory_peak_mb=0,
                memory_delta_mb=0,
                cpu_percent=0,
                chunks_found=0,
                entities_found=0,
                total_text_length=0,
                fire_content_chunks=0,
                toc_detection_score=0,
                content_diversity_score=0,
                success=False,
                error_message=f"Failed to initialize parser: {e}"
            )
        
        # Measure CPU before
        cpu_before = psutil.cpu_percent(interval=None)
        
        # Run parser with memory monitoring
        measurement = self._measure_memory_usage(
            parser.extract_fire_sections, str(pdf_path)
        )
        
        # Measure CPU after
        cpu_after = psutil.cpu_percent(interval=None)
        cpu_usage = max(0, cpu_after - cpu_before)
        
        # Analyze output
        analysis = self._analyze_parser_output(measurement['result'], parser_name)
        
        return BenchmarkResult(
            parser_name=parser_name,
            pdf_name=pdf_path.name,
            parse_time_seconds=measurement['execution_time'],
            memory_peak_mb=measurement['memory_peak'],
            memory_delta_mb=measurement['memory_delta'],
            cpu_percent=cpu_usage,
            chunks_found=analysis['chunks_found'],
            entities_found=analysis['entities_found'],
            total_text_length=analysis['total_text_length'],
            fire_content_chunks=analysis['fire_content_chunks'],
            toc_detection_score=analysis['toc_detection_score'],
            content_diversity_score=analysis['content_diversity_score'],
            success=measurement['success'],
            error_message=measurement['error']
        )
    
    def run_full_benchmark(self) -> Dict[str, List[BenchmarkResult]]:
        """Run comprehensive benchmark across all parsers and PDFs."""
        print("🚀 Starting Comprehensive Parser Benchmark")
        print("=" * 50)
        
        # Find all PDFs
        pdf_files = list(self.specs_dir.glob("*.pdf"))
        print(f"Found {len(pdf_files)} PDFs to test")
        print(f"Found {len(self.available_parsers)} parsers to benchmark")
        
        results_by_parser = {}
        
        for parser_name in self.available_parsers:
            print(f"\n📈 Benchmarking {parser_name}")
            print("-" * 30)
            
            parser_results = []
            for pdf_path in pdf_files:
                result = self.benchmark_parser(parser_name, pdf_path)
                parser_results.append(result)
                self.results.append(result)
                
                # Quick summary
                if result.success:
                    print(f"    ✓ {pdf_path.name}: {result.chunks_found} chunks, {result.parse_time_seconds:.2f}s")
                else:
                    print(f"    ✗ {pdf_path.name}: {result.error_message}")
                    
            results_by_parser[parser_name] = parser_results
            
        return results_by_parser
    
    def calculate_grades(self, results_by_parser: Dict[str, List[BenchmarkResult]]) -> Dict[str, ParserGrade]:
        """Calculate comprehensive grades for each parser."""
        print(f"\n🎓 Calculating Parser Grades")
        print("=" * 30)
        
        grades = {}
        
        # Collect all performance metrics for relative grading
        all_times = [r.parse_time_seconds for r in self.results if r.success]
        all_memory = [r.memory_peak_mb for r in self.results if r.success]
        all_chunks = [r.chunks_found for r in self.results if r.success]
        
        for parser_name, results in results_by_parser.items():
            successful_results = [r for r in results if r.success]
            
            if not successful_results:
                # Parser failed on all tests
                grades[parser_name] = ParserGrade(
                    parser_name=parser_name,
                    speed_grade=0, memory_grade=0, reliability_grade=0,
                    chunk_detection_grade=0, entity_extraction_grade=0, content_quality_grade=0,
                    performance_grade=0, accuracy_grade=0, overall_grade=0,
                    tests_run=len(results), successful_tests=0,
                    avg_parse_time=0, avg_chunks_found=0
                )
                continue
                
            # Calculate performance grades
            avg_time = statistics.mean([r.parse_time_seconds for r in successful_results])
            avg_memory = statistics.mean([r.memory_peak_mb for r in successful_results])
            
            # Speed grade (faster = better, scaled 0-100)
            if all_times and len(all_times) > 1:
                min_time = min(all_times)
                max_time = max(all_times) 
                speed_grade = max(0, 100 - ((avg_time - min_time) / (max_time - min_time + 0.001)) * 100)
            else:
                speed_grade = 75  # Default for single parser
                
            # Memory grade (less memory = better)
            if all_memory and len(all_memory) > 1:
                min_memory = min(all_memory)
                max_memory = max(all_memory)
                memory_grade = max(0, 100 - ((avg_memory - min_memory) / (max_memory - min_memory + 0.001)) * 100)
            else:
                memory_grade = 75  # Default for single parser
                
            # Reliability grade (success rate)
            reliability_grade = (len(successful_results) / len(results)) * 100
            
            # Accuracy grades
            avg_chunks = statistics.mean([r.chunks_found for r in successful_results])
            avg_fire_content = statistics.mean([r.fire_content_chunks for r in successful_results])
            avg_toc_score = statistics.mean([r.toc_detection_score for r in successful_results])
            avg_diversity = statistics.mean([r.content_diversity_score for r in successful_results])
            
            # Chunk detection grade (more chunks = better, but diminishing returns)
            if all_chunks:
                max_chunks = max(all_chunks) if all_chunks else 1
                chunk_detection_grade = min(100, (avg_chunks / (max_chunks + 1)) * 100)
            else:
                chunk_detection_grade = 0
                
            # Entity extraction grade (based on fire content detection)
            entity_extraction_grade = min(100, (avg_fire_content / max(avg_chunks, 1)) * 100)
            
            # Content quality grade (combination of TOC detection and diversity)
            content_quality_grade = (avg_toc_score + min(100, avg_diversity * 2)) / 2
            
            # Calculate composite grades
            performance_grade = (speed_grade + memory_grade + reliability_grade) / 3
            accuracy_grade = (chunk_detection_grade + entity_extraction_grade + content_quality_grade) / 3
            overall_grade = (performance_grade + accuracy_grade) / 2
            
            grades[parser_name] = ParserGrade(
                parser_name=parser_name,
                speed_grade=speed_grade,
                memory_grade=memory_grade,
                reliability_grade=reliability_grade,
                chunk_detection_grade=chunk_detection_grade,
                entity_extraction_grade=entity_extraction_grade,
                content_quality_grade=content_quality_grade,
                performance_grade=performance_grade,
                accuracy_grade=accuracy_grade,
                overall_grade=overall_grade,
                tests_run=len(results),
                successful_tests=len(successful_results),
                avg_parse_time=avg_time,
                avg_chunks_found=avg_chunks
            )
            
        return grades
    
    def generate_report(self, results_by_parser: Dict[str, List[BenchmarkResult]], 
                       grades: Dict[str, ParserGrade]) -> str:
        """Generate comprehensive benchmark report."""
        report = []
        report.append("📊 COMPREHENSIVE PARSER BENCHMARK REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Parsers tested: {len(self.available_parsers)}")
        report.append(f"PDFs tested: {len(list(self.specs_dir.glob('*.pdf')))}")
        report.append(f"Total tests run: {len(self.results)}")
        
        # Overall rankings
        report.append("\n🏆 PARSER RANKINGS")
        report.append("-" * 30)
        sorted_grades = sorted(grades.values(), key=lambda g: g.overall_grade, reverse=True)
        
        for i, grade in enumerate(sorted_grades, 1):
            grade_letter = self._get_grade_letter(grade.overall_grade)
            report.append(f"{i}. {grade.parser_name:<25} {grade.overall_grade:5.1f} ({grade_letter})")
            
        # Detailed grades by category
        report.append("\n📈 DETAILED GRADES")
        report.append("-" * 30)
        report.append(f"{'Parser':<25} {'Speed':<8} {'Memory':<8} {'Reliab':<8} {'Chunks':<8} {'Quality':<8} {'Overall':<8}")
        report.append("-" * 80)
        
        for grade in sorted_grades:
            report.append(f"{grade.parser_name:<25} "
                         f"{grade.speed_grade:>6.1f}  "
                         f"{grade.memory_grade:>6.1f}  "
                         f"{grade.reliability_grade:>6.1f}  "
                         f"{grade.chunk_detection_grade:>6.1f}  "
                         f"{grade.content_quality_grade:>6.1f}  "
                         f"{grade.overall_grade:>6.1f}")
                         
        # Performance statistics
        report.append("\n⚡ PERFORMANCE STATISTICS")
        report.append("-" * 30)
        
        for parser_name, grade in grades.items():
            if grade.successful_tests > 0:
                report.append(f"\n{parser_name}:")
                report.append(f"  Success rate: {grade.successful_tests}/{grade.tests_run} ({grade.reliability_grade:.1f}%)")
                report.append(f"  Avg parse time: {grade.avg_parse_time:.3f} seconds")
                report.append(f"  Avg chunks found: {grade.avg_chunks_found:.1f}")
                
                # Best and worst performance
                parser_results = [r for r in results_by_parser[parser_name] if r.success]
                if parser_results:
                    fastest = min(parser_results, key=lambda r: r.parse_time_seconds)
                    slowest = max(parser_results, key=lambda r: r.parse_time_seconds)
                    most_chunks = max(parser_results, key=lambda r: r.chunks_found)
                    
                    report.append(f"  Fastest: {fastest.pdf_name} ({fastest.parse_time_seconds:.3f}s)")
                    report.append(f"  Slowest: {slowest.pdf_name} ({slowest.parse_time_seconds:.3f}s)")
                    report.append(f"  Most chunks: {most_chunks.pdf_name} ({most_chunks.chunks_found} chunks)")
                    
        # Recommendations
        report.append("\n💡 RECOMMENDATIONS")
        report.append("-" * 30)
        
        if sorted_grades:
            best_overall = sorted_grades[0]
            best_speed = max(grades.values(), key=lambda g: g.speed_grade)
            best_accuracy = max(grades.values(), key=lambda g: g.accuracy_grade)
            
            report.append(f"🥇 Best overall: {best_overall.parser_name} (Grade: {best_overall.overall_grade:.1f})")
            report.append(f"⚡ Fastest: {best_speed.parser_name} (Speed grade: {best_speed.speed_grade:.1f})")
            report.append(f"🎯 Most accurate: {best_accuracy.parser_name} (Accuracy grade: {best_accuracy.accuracy_grade:.1f})")
        
        return "\n".join(report)
    
    def _get_grade_letter(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90: return "A"
        elif score >= 80: return "B"
        elif score >= 70: return "C"
        elif score >= 60: return "D"
        else: return "F"
    
    def save_detailed_results(self, results_by_parser: Dict[str, List[BenchmarkResult]], 
                             grades: Dict[str, ParserGrade], output_dir: Path):
        """Save detailed results to JSON files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        # Save raw results
        raw_results = {}
        for parser_name, results in results_by_parser.items():
            raw_results[parser_name] = [
                {
                    'pdf_name': r.pdf_name,
                    'parse_time_seconds': r.parse_time_seconds,
                    'memory_peak_mb': r.memory_peak_mb,
                    'chunks_found': r.chunks_found,
                    'entities_found': r.entities_found,
                    'fire_content_chunks': r.fire_content_chunks,
                    'toc_detection_score': r.toc_detection_score,
                    'content_diversity_score': r.content_diversity_score,
                    'success': r.success,
                    'error_message': r.error_message
                }
                for r in results
            ]
            
        with open(output_dir / f'benchmark_raw_{timestamp}.json', 'w') as f:
            json.dump(raw_results, f, indent=2)
            
        # Save grades
        grades_data = {}
        for parser_name, grade in grades.items():
            grades_data[parser_name] = {
                'overall_grade': grade.overall_grade,
                'performance_grade': grade.performance_grade,
                'accuracy_grade': grade.accuracy_grade,
                'speed_grade': grade.speed_grade,
                'memory_grade': grade.memory_grade,
                'reliability_grade': grade.reliability_grade,
                'chunk_detection_grade': grade.chunk_detection_grade,
                'entity_extraction_grade': grade.entity_extraction_grade,
                'content_quality_grade': grade.content_quality_grade,
                'tests_run': grade.tests_run,
                'successful_tests': grade.successful_tests,
                'avg_parse_time': grade.avg_parse_time,
                'avg_chunks_found': grade.avg_chunks_found
            }
            
        with open(output_dir / f'benchmark_grades_{timestamp}.json', 'w') as f:
            json.dump(grades_data, f, indent=2)
            
        print(f"📁 Detailed results saved to {output_dir}")

def main():
    """Main function to run comprehensive benchmarks."""
    specs_dir = Path(__file__).parent.parent / "specs"
    reports_dir = Path(__file__).parent.parent / "reports"
    
    if not specs_dir.exists():
        print(f"❌ Specs directory not found: {specs_dir}")
        return
        
    benchmark = ParserBenchmark(specs_dir)
    
    if not benchmark.available_parsers:
        print("❌ No parsers found to benchmark!")
        return
        
    # Run benchmarks
    results_by_parser = benchmark.run_full_benchmark()
    grades = benchmark.calculate_grades(results_by_parser)
    
    # Generate and display report
    report = benchmark.generate_report(results_by_parser, grades)
    print(f"\n{report}")
    
    # Save detailed results
    benchmark.save_detailed_results(results_by_parser, grades, reports_dir)
    
    # Save text report
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    with open(reports_dir / f'benchmark_report_{timestamp}.txt', 'w') as f:
        f.write(report)
    
    print(f"\n📊 Benchmark complete! Report saved to reports/")

if __name__ == "__main__":
    main() 
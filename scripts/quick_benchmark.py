#!/usr/bin/env python3
"""
Quick Parser Benchmark & Grading Tool

Run this script to get instant grades for all your parsers:
python3 scripts/quick_benchmark.py

Generates:
- Performance grades (A-F)
- Speed metrics
- Accuracy scores
- Detailed recommendations
"""

import sys
import time
import json
import importlib.util
import statistics
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

@dataclass
class ParserScore:
    name: str
    overall_grade: float
    speed_grade: float
    accuracy_grade: float
    quality_grade: float
    reliability_grade: float
    success_rate: float
    avg_time: float
    avg_chunks: float
    total_tests: int

class QuickBenchmark:
    def __init__(self):
        self.parsers_dir = Path("..") / "parsers"
        self.specs_dir = Path("specs")
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        
    def discover_parsers(self) -> Dict[str, Any]:
        """Find and load all available parsers."""
        parsers = {}
        parser_mapping = {
            'toc_driven_chunker.cpython-313.pyc': ('toc_driven_chunker', 'TOCDrivenChunker'),
            'production_chunker.cpython-313.pyc': ('production_chunker', 'ProductionSpecChunker'),
            'page_scoring.cpython-313.pyc': ('page_scoring', 'PageScorer'),
            'section_stitcher.cpython-313.pyc': ('section_stitcher', 'SectionStitcher')
        }
        
        for pyc_file, (module_name, class_name) in parser_mapping.items():
            pyc_path = self.parsers_dir / pyc_file
            if pyc_path.exists():
                try:
                    spec = importlib.util.spec_from_file_location(module_name, str(pyc_path))
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    
                    parser_class = getattr(module, class_name)
                    parsers[module_name] = parser_class
                    
                except Exception as e:
                    print(f"⚠️  Failed to load {module_name}: {e}")
                    
        return parsers
    
    def test_parser(self, parser_name: str, parser_class: Any, pdf_files: List[Path]) -> Dict[str, Any]:
        """Test a single parser on multiple PDFs."""
        results = []
        
        for pdf_path in pdf_files[:3]:  # Test first 3 PDFs for speed
            try:
                parser = parser_class()
                
                # Check if parser has the right method
                if not hasattr(parser, 'extract_fire_sections'):
                    results.append({
                        'pdf': pdf_path.name,
                        'success': False,
                        'error': 'Missing extract_fire_sections method',
                        'time': 0,
                        'chunks': 0,
                        'fire_score': 0,
                        'toc_score': 0
                    })
                    continue
                
                start_time = time.time()
                result = parser.extract_fire_sections(str(pdf_path))
                end_time = time.time()
                
                parse_time = end_time - start_time
                chunks_found = len(result.get('chunks', [])) if isinstance(result, dict) else 0
                
                # Analyze content quality
                fire_score = 0
                toc_score = 0
                if isinstance(result, dict) and 'chunks' in result:
                    for chunk in result['chunks']:
                        text = chunk.get('text', '').lower()
                        if any(word in text for word in ['fire', 'suppression', 'sprinkler', 'protection']):
                            fire_score += 1
                        if any(word in text for word in ['table', 'contents', 'section', 'division']):
                            toc_score += 1
                
                results.append({
                    'pdf': pdf_path.name,
                    'success': True,
                    'time': parse_time,
                    'chunks': chunks_found,
                    'fire_score': fire_score,
                    'toc_score': toc_score
                })
                
            except Exception as e:
                results.append({
                    'pdf': pdf_path.name,
                    'success': False,
                    'error': str(e),
                    'time': 0,
                    'chunks': 0,
                    'fire_score': 0,
                    'toc_score': 0
                })
                
        return results
    
    def calculate_grade(self, parser_name: str, results: List[Dict]) -> ParserScore:
        """Calculate comprehensive grade for a parser."""
        successful = [r for r in results if r['success']]
        total_tests = len(results)
        success_rate = len(successful) / total_tests if total_tests > 0 else 0
        
        if not successful:
            return ParserScore(
                name=parser_name,
                overall_grade=0, speed_grade=0, accuracy_grade=0,
                quality_grade=0, reliability_grade=0,
                success_rate=0, avg_time=0, avg_chunks=0,
                total_tests=total_tests
            )
        
        # Calculate metrics
        avg_time = statistics.mean([r['time'] for r in successful])
        avg_chunks = statistics.mean([r['chunks'] for r in successful])
        avg_fire = statistics.mean([r['fire_score'] for r in successful])
        avg_toc = statistics.mean([r['toc_score'] for r in successful])
        
        # Grade calculations (0-100)
        speed_grade = max(0, 100 - (avg_time * 15))  # Penalty for slow parsing
        accuracy_grade = min(100, avg_chunks * 8)     # Reward for finding chunks
        quality_grade = min(100, (avg_fire + avg_toc) * 12)  # Reward for relevant content
        reliability_grade = success_rate * 100
        
        overall_grade = (speed_grade + accuracy_grade + quality_grade + reliability_grade) / 4
        
        return ParserScore(
            name=parser_name,
            overall_grade=overall_grade,
            speed_grade=speed_grade,
            accuracy_grade=accuracy_grade,
            quality_grade=quality_grade,
            reliability_grade=reliability_grade,
            success_rate=success_rate,
            avg_time=avg_time,
            avg_chunks=avg_chunks,
            total_tests=total_tests
        )
    
    def get_grade_letter(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90: return "A"
        elif score >= 80: return "B"
        elif score >= 70: return "C"
        elif score >= 60: return "D"
        else: return "F"
    
    def run_benchmark(self) -> List[ParserScore]:
        """Run complete benchmark."""
        print("🚀 QUICK PARSER BENCHMARK")
        print("=" * 40)
        
        # Discover parsers and PDFs
        parsers = self.discover_parsers()
        pdf_files = list(self.specs_dir.glob("*.pdf"))
        
        print(f"📄 Testing {len(pdf_files)} PDFs")
        print(f"🔧 Found {len(parsers)} parsers")
        print()
        
        # Test each parser
        scores = []
        for parser_name, parser_class in parsers.items():
            print(f"Testing {parser_name}...")
            results = self.test_parser(parser_name, parser_class, pdf_files)
            score = self.calculate_grade(parser_name, results)
            scores.append(score)
            
            # Quick status
            status = "✅" if score.success_rate > 0.5 else "❌"
            print(f"  {status} Grade: {score.overall_grade:.1f} ({self.get_grade_letter(score.overall_grade)})")
        
        return sorted(scores, key=lambda s: s.overall_grade, reverse=True)
    
    def generate_report(self, scores: List[ParserScore]) -> str:
        """Generate benchmark report."""
        report = []
        report.append("📊 PARSER BENCHMARK REPORT")
        report.append("=" * 40)
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Parsers tested: {len(scores)}")
        report.append()
        
        # Rankings
        report.append("🏆 RANKINGS")
        report.append("-" * 20)
        for i, score in enumerate(scores, 1):
            grade_letter = self.get_grade_letter(score.overall_grade)
            report.append(f"{i}. {score.name:<25} {score.overall_grade:5.1f} ({grade_letter})")
        
        report.append()
        
        # Detailed grades
        report.append("📈 DETAILED GRADES")
        report.append("-" * 20)
        report.append(f"{'Parser':<25} {'Overall':<8} {'Speed':<8} {'Accuracy':<10} {'Quality':<8} {'Reliability':<12}")
        report.append("-" * 80)
        
        for score in scores:
            report.append(f"{score.name:<25} "
                         f"{score.overall_grade:>5.1f} ({self.get_grade_letter(score.overall_grade)}) "
                         f"{score.speed_grade:>5.1f} ({self.get_grade_letter(score.speed_grade)}) "
                         f"{score.accuracy_grade:>7.1f} ({self.get_grade_letter(score.accuracy_grade)}) "
                         f"{score.quality_grade:>5.1f} ({self.get_grade_letter(score.quality_grade)}) "
                         f"{score.reliability_grade:>9.1f} ({self.get_grade_letter(score.reliability_grade)})")
        
        report.append()
        
        # Performance stats
        report.append("⚡ PERFORMANCE STATS")
        report.append("-" * 20)
        for score in scores:
            if score.success_rate > 0:
                report.append(f"{score.name}:")
                report.append(f"  • Success rate: {score.success_rate*100:.0f}%")
                report.append(f"  • Avg time: {score.avg_time:.3f}s")
                report.append(f"  • Avg chunks: {score.avg_chunks:.1f}")
                report.append()
        
        # Recommendations
        if scores:
            best = scores[0]
            report.append("💡 RECOMMENDATIONS")
            report.append("-" * 20)
            report.append(f"🥇 Best parser: {best.name} (Grade: {best.overall_grade:.1f})")
            
            if best.speed_grade < 70:
                report.append("⚡ Speed improvement needed")
            if best.accuracy_grade < 80:
                report.append("🎯 Accuracy tuning recommended")
            if best.quality_grade < 80:
                report.append("🔍 Content filtering needs adjustment")
                
            # Find parsers that need fixing
            broken_parsers = [s for s in scores if s.success_rate == 0]
            if broken_parsers:
                report.append(f"🔧 Fix API compatibility: {', '.join(p.name for p in broken_parsers)}")
        
        return "\n".join(report)
    
    def save_results(self, scores: List[ParserScore], report: str):
        """Save benchmark results."""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        # Save detailed results
        results_data = []
        for score in scores:
            results_data.append({
                'name': score.name,
                'overall_grade': score.overall_grade,
                'speed_grade': score.speed_grade,
                'accuracy_grade': score.accuracy_grade,
                'quality_grade': score.quality_grade,
                'reliability_grade': score.reliability_grade,
                'success_rate': score.success_rate,
                'avg_time': score.avg_time,
                'avg_chunks': score.avg_chunks,
                'total_tests': score.total_tests
            })
        
        with open(self.reports_dir / f'benchmark_results_{timestamp}.json', 'w') as f:
            json.dump(results_data, f, indent=2)
        
        # Save text report
        with open(self.reports_dir / f'benchmark_report_{timestamp}.txt', 'w') as f:
            f.write(report)
        
        print(f"📁 Results saved to reports/")

def main():
    """Run quick benchmark."""
    benchmark = QuickBenchmark()
    
    try:
        scores = benchmark.run_benchmark()
        report = benchmark.generate_report(scores)
        
        print("\n" + report)
        
        benchmark.save_results(scores, report)
        print("\n✅ Quick benchmark complete!")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
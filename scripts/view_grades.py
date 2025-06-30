#!/usr/bin/env python3
"""
Parser Grades Viewer

Quick way to view the latest parser performance grades.
Run: python3 scripts/view_grades.py
"""

import json
import sys
from pathlib import Path
import glob

def grade_letter(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90: return "A"
    elif score >= 80: return "B"
    elif score >= 70: return "C"
    elif score >= 60: return "D"
    else: return "F"

def get_latest_grades():
    """Get the most recent parser grades."""
    reports_dir = Path("reports")
    
    if not reports_dir.exists():
        print("❌ No reports directory found!")
        return None
        
    # Find latest grades file
    grade_files = list(reports_dir.glob("parser_grades_*.json"))
    
    if not grade_files:
        print("❌ No parser grades found! Run a benchmark first.")
        return None
        
    latest_file = max(grade_files, key=lambda f: f.stat().st_mtime)
    
    with open(latest_file, 'r') as f:
        grades = json.load(f)
        
    print(f"📊 Latest grades from: {latest_file.name}")
    return grades

def display_grades(grades):
    """Display grades in a nice format."""
    print("\n🎓 PARSER REPORT CARD")
    print("=" * 50)
    
    # Sort by overall grade
    sorted_parsers = sorted(grades.items(), key=lambda x: x[1]['overall'], reverse=True)
    
    print("\n🏆 RANKINGS")
    print("-" * 25)
    for i, (parser_name, grade) in enumerate(sorted_parsers, 1):
        letter = grade_letter(grade['overall'])
        status = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
        print(f"{status} {i}. {parser_name:<20} {grade['overall']:5.1f} ({letter})")
    
    print(f"\n📈 DETAILED GRADES")
    print("-" * 50)
    print(f"{'Parser':<20} {'Overall':<8} {'Speed':<8} {'Accuracy':<9} {'Quality':<8}")
    print("-" * 55)
    
    for parser_name, grade in sorted_parsers:
        print(f"{parser_name:<20} "
              f"{grade['overall']:>5.1f} ({grade_letter(grade['overall'])}) "
              f"{grade['speed']:>5.1f} ({grade_letter(grade['speed'])}) "
              f"{grade['accuracy']:>7.1f} ({grade_letter(grade['accuracy'])}) "
              f"{grade['quality']:>5.1f} ({grade_letter(grade['quality'])})")
    
    print(f"\n⚡ PERFORMANCE SUMMARY")
    print("-" * 30)
    
    working_parsers = [(name, grade) for name, grade in grades.items() if grade['success_rate'] > 0]
    
    if working_parsers:
        best = max(working_parsers, key=lambda x: x[1]['overall'])
        fastest = min(working_parsers, key=lambda x: x[1]['avg_time'])
        most_accurate = max(working_parsers, key=lambda x: x[1]['accuracy'])
        
        print(f"🏆 Best overall: {best[0]} (Grade: {best[1]['overall']:.1f})")
        print(f"⚡ Fastest: {fastest[0]} ({fastest[1]['avg_time']:.2f}s avg)")
        print(f"🎯 Most accurate: {most_accurate[0]} ({most_accurate[1]['avg_chunks']:.1f} chunks avg)")
        
        print(f"\n💡 QUICK INSIGHTS")
        print("-" * 20)
        
        broken_parsers = [name for name, grade in grades.items() if grade['success_rate'] == 0]
        if broken_parsers:
            print(f"🔧 Need API fixes: {', '.join(broken_parsers)}")
            
        slow_parsers = [name for name, grade in grades.items() if grade['speed'] < 60 and grade['success_rate'] > 0]
        if slow_parsers:
            print(f"🐌 Need speed optimization: {', '.join(slow_parsers)}")
            
        if best[1]['overall'] >= 90:
            print(f"✨ {best[0]} is production-ready! (A grade)")
        elif best[1]['overall'] >= 80:
            print(f"👍 {best[0]} is good with minor improvements (B grade)")
        else:
            print(f"⚠️ All parsers need significant improvement")
    else:
        print("❌ No working parsers found!")
    
    print(f"\n📈 Run benchmark again: python3 -c 'import subprocess; subprocess.run([\"python3\", \"-c\", \"# benchmark code here\"])'")

def main():
    """Main function."""
    print("📊 PARSER GRADES DASHBOARD")
    print("=" * 30)
    
    grades = get_latest_grades()
    
    if grades:
        display_grades(grades)
    else:
        print("\n💡 To generate grades, run a benchmark first:")
        print("   python3 scripts/quick_benchmark.py")
    
    print("\n✅ Grade viewing complete!")

if __name__ == "__main__":
    main() 
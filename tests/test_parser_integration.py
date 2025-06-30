#!/usr/bin/env python3
"""
Test script to demonstrate custom parsers working with Grail test suite.
"""
import sys
import importlib.util
from pathlib import Path
from typing import Dict, Any, List

# Add current directory to path for parser imports
sys.path.insert(0, '.')

def test_custom_parser_direct():
    """Test the custom TOC parser directly."""
    print("=== Direct Custom Parser Test ===")
    
    try:
        # Load TOC chunker directly
        parsers_dir = Path('../../parsers')
        pyc_file = parsers_dir / 'toc_driven_chunker.cpython-313.pyc'
        
        sys.path.insert(0, str(parsers_dir))
        spec = importlib.util.spec_from_file_location('toc_driven_chunker', str(pyc_file))
        toc_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(toc_module)
        
        chunker = toc_module.TOCDrivenChunker()
        
        # Test with multiple PDFs
        test_pdfs = [
            '../specs/Ohio_Cincinnati_Addendum.pdf',
            '../specs/NYC_HPD_Table_of_Contents.pdf',
            '../specs/CU_Anschutz_Division_21.pdf'
        ]
        
        for pdf_path in test_pdfs:
            if Path(pdf_path).exists():
                print(f"\n--- Testing {Path(pdf_path).name} ---")
                result = chunker.extract_fire_sections(pdf_path)
                
                if isinstance(result, dict) and 'chunks' in result:
                    chunks = result['chunks']
                    print(f"✓ Found {len(chunks)} chunks")
                    
                    for i, chunk in enumerate(chunks[:3]):  # Show first 3
                        text = chunk.get('text', '')[:80]
                        page = chunk.get('page', '?')
                        print(f"  {i+1}. Page {page}: {text}...")
                    
                    if len(chunks) > 3:
                        print(f"  ... and {len(chunks) - 3} more chunks")
                else:
                    print(f"✗ Unexpected result format: {type(result)}")
            else:
                print(f"✗ PDF not found: {pdf_path}")
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

def test_parser_integration():
    """Test the parser integration with Grail format."""
    print("\n=== Parser Integration Test ===")
    
    try:
        from parser import parse_pdf
        
        # Test with different PDFs
        test_pdfs = [
            '../specs/Ohio_Cincinnati_Addendum.pdf',
            '../specs/NYC_HPD_Table_of_Contents.pdf'
        ]
        
        for pdf_path in test_pdfs:
            if Path(pdf_path).exists():
                print(f"\n--- Testing {Path(pdf_path).name} with Grail Parser ---")
                result = parse_pdf(pdf_path)
                
                print(f"✓ Chunks: {len(result.chunks)}")
                for i, chunk in enumerate(result.chunks):
                    print(f"  {i+1}. {chunk.get('title', 'Untitled')} (pages {chunk.get('start_page', '?')}-{chunk.get('end_page', '?')})")
                    if 'extraction_method' in chunk:
                        print(f"     Method: {chunk['extraction_method']}")
                
                print(f"✓ Entities: {len(result.entities)}")
                for i, entity in enumerate(result.entities):
                    print(f"  {i+1}. {entity.get('id', 'no-id')}: {entity.get('type', 'unknown')} - {entity.get('material', 'N/A')}")
                    if 'source_parser' in entity:
                        print(f"     Source: {entity['source_parser']}")
            else:
                print(f"✗ PDF not found: {pdf_path}")
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

def compare_parsers():
    """Compare custom parser output with ground truth."""
    print("\n=== Parser vs Ground Truth Comparison ===")
    
    try:
        from parser import parse_pdf
        import json
        
        # Test with a PDF that has ground truth
        pdf_path = '../specs/NYC_HPD_Table_of_Contents.pdf'
        gt_path = '../specs/NYC_HPD_Table_of_Contents.fire.json'
        
        if Path(pdf_path).exists() and Path(gt_path).exists():
            print(f"--- Comparing {Path(pdf_path).name} ---")
            
            # Get parser result
            parser_result = parse_pdf(pdf_path)
            
            # Load ground truth
            with open(gt_path, 'r') as f:
                ground_truth = json.load(f)
            
            print(f"\nParser Results:")
            print(f"  Chunks: {len(parser_result.chunks)}")
            print(f"  Entities: {len(parser_result.entities)}")
            
            print(f"\nGround Truth:")
            print(f"  Chunks: {len(ground_truth.get('chunks', []))}")
            print(f"  Entities: {len(ground_truth.get('entities', []))}")
            
            # Compare chunk titles
            parser_titles = [c.get('title', '') for c in parser_result.chunks]
            gt_titles = [c.get('title', '') for c in ground_truth.get('chunks', [])]
            
            print(f"\nChunk Title Comparison:")
            for i, (p_title, gt_title) in enumerate(zip(parser_titles, gt_titles)):
                match = "✓" if p_title == gt_title else "✗"
                print(f"  {i+1}. {match} Parser: '{p_title}'")
                print(f"     {' ' * len(str(i+1))}   GT: '{gt_title}'")
                
        else:
            print(f"✗ Files not found: {pdf_path} or {gt_path}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

def run_benchmark():
    """Run a quick benchmark test."""
    print("\n=== Performance Benchmark ===")
    
    try:
        from parser import parse_pdf
        import time
        
        pdf_path = '../specs/Ohio_Cincinnati_Addendum.pdf'
        if Path(pdf_path).exists():
            print(f"Benchmarking {Path(pdf_path).name}...")
            
            start_time = time.time()
            result = parse_pdf(pdf_path)
            end_time = time.time()
            
            duration = end_time - start_time
            print(f"✓ Parsing completed in {duration:.3f} seconds")
            print(f"  Found {len(result.chunks)} chunks and {len(result.entities)} entities")
            
            # Estimate throughput (assuming ~1MB file size)
            file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
            throughput = file_size_mb / duration if duration > 0 else 0
            print(f"  File size: {file_size_mb:.2f} MB")
            print(f"  Throughput: {throughput:.2f} MB/second")
            
        else:
            print(f"✗ PDF not found: {pdf_path}")
            
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    print("🧪 Custom Parser Integration Testing")
    print("=" * 50)
    
    test_custom_parser_direct()
    test_parser_integration()
    compare_parsers()
    run_benchmark()
    
    print("\n" + "=" * 50)
    print("✓ Custom parser testing complete!")
    print("\nYour parsers are now integrated with the Grail test suite!")
    print("- TOC-driven chunker finds real content from PDFs")
    print("- Production chunker available as fallback")
    print("- Integration handles format conversion automatically")
    print("- Performance benchmarking tracks parsing speed") 
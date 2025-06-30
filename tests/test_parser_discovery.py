#!/usr/bin/env python3
"""
Test script to discover and run parsers from ../parsers/ against Grail test suite.
"""
import sys
import os
import importlib.util
from pathlib import Path
from typing import List, Dict, Any

# Add parsers directory to Python path
parsers_dir = Path(__file__).parent.parent.parent / "parsers"
sys.path.insert(0, str(parsers_dir))

def discover_parsers():
    """Discover available parsers in the parsers directory."""
    parsers = []
    
    # Look for compiled Python files
    pyc_files = list(parsers_dir.glob("*.pyc"))
    
    print(f"Found {len(pyc_files)} compiled Python files:")
    for pyc_file in pyc_files:
        print(f"  - {pyc_file.name}")
    
    # Try to import them
    for pyc_file in pyc_files:
        module_name = pyc_file.stem.split('.')[0]  # Remove .cpython-313
        try:
            # Try to import the module
            module = importlib.import_module(module_name)
            parsers.append((module_name, module))
            print(f"✓ Successfully imported {module_name}")
        except Exception as e:
            print(f"✗ Failed to import {module_name}: {e}")
    
    return parsers

def test_parser_interface(module_name, module):
    """Test if a parser module has the required interface."""
    print(f"\n=== Testing {module_name} ===")
    
    # Check for parse function
    if hasattr(module, 'parse_pdf'):
        print("✓ Has parse_pdf function")
        
        # Try to get function signature
        import inspect
        sig = inspect.signature(module.parse_pdf)
        print(f"  Signature: {sig}")
        
        # Test with a sample PDF
        test_pdf = "../specs/NYC_HPD_Table_of_Contents.pdf"
        if Path(test_pdf).exists():
            try:
                result = module.parse_pdf(test_pdf)
                print(f"✓ Successfully parsed test PDF")
                print(f"  Result type: {type(result)}")
                
                # Analyze result structure
                if hasattr(result, 'chunks'):
                    print(f"  Chunks: {len(result.chunks)}")
                elif isinstance(result, dict) and 'chunks' in result:
                    print(f"  Chunks: {len(result['chunks'])}")
                elif isinstance(result, tuple):
                    print(f"  Result is tuple with {len(result)} elements")
                    for i, elem in enumerate(result):
                        print(f"    Element {i}: {type(elem)}")
                else:
                    print(f"  Result structure: {result}")
                    
            except Exception as e:
                print(f"✗ Failed to parse test PDF: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"✗ Test PDF not found: {test_pdf}")
    else:
        print("✗ No parse_pdf function found")
        
        # List available functions/classes
        members = [name for name in dir(module) if not name.startswith('_')]
        print(f"  Available members: {members}")

def main():
    print("=== Grail Parser Discovery & Testing ===")
    
    # Discover parsers
    parsers = discover_parsers()
    
    if not parsers:
        print("\nNo parsers found. Please check the parsers directory.")
        return
    
    # Test each parser
    for module_name, module in parsers:
        test_parser_interface(module_name, module)
    
    print(f"\n=== Summary ===")
    print(f"Found {len(parsers)} importable modules")

if __name__ == "__main__":
    main() 
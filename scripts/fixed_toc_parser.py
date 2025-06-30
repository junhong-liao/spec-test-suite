#!/usr/bin/env python3
"""
Fixed TOC Parser Wrapper

This wrapper fixes the page range mapping issue in the original TOC parser
and provides cleaner output with proper page_start/page_end fields.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

class FixedTOCParser:
    """Wrapper around TOCDrivenChunker that fixes page range issues."""
    
    def __init__(self):
        # Load the original TOC parser
        parsers_dir = Path(__file__).parent.parent / "parsers"
        pyc_path = parsers_dir / "toc_driven_chunker.cpython-313.pyc"
        
        if not pyc_path.exists():
            raise FileNotFoundError(f"TOC parser not found: {pyc_path}")
        
        spec = importlib.util.spec_from_file_location("toc_driven_chunker", str(pyc_path))
        module = importlib.util.module_from_spec(spec)
        sys.modules["toc_driven_chunker"] = module
        spec.loader.exec_module(module)
        
        self.original_parser = module.TOCDrivenChunker()
    
    def _parse_page_range(self, page_range_str: str) -> tuple[Optional[int], Optional[int]]:
        """Parse page range string like '6-7' or '42' into start/end pages."""
        if not page_range_str or page_range_str == "None":
            return None, None
        
        try:
            if '-' in page_range_str:
                parts = page_range_str.split('-')
                start = int(parts[0].strip()) if parts[0].strip() else None
                end = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else start
                return start, end
            else:
                page = int(page_range_str.strip())
                return page, page
        except (ValueError, AttributeError):
            return None, None
    
    def extract_fire_sections(self, pdf_path: str) -> Dict[str, Any]:
        """Extract fire sections with fixed page ranges."""
        # Get original result
        result = self.original_parser.extract_fire_sections(pdf_path)
        
        # Fix chunks to have proper page_start/page_end
        if 'chunks' in result:
            fixed_chunks = []
            for chunk in result['chunks']:
                fixed_chunk = chunk.copy()
                
                # Try to get page info from various fields
                page_start, page_end = None, None
                
                # Check for page_range field
                if 'page_range' in chunk:
                    page_start, page_end = self._parse_page_range(str(chunk['page_range']))
                
                # Fallback to page field
                elif 'page' in chunk and chunk['page'] is not None:
                    try:
                        page = int(chunk['page'])
                        page_start, page_end = page, page
                    except (ValueError, TypeError):
                        pass
                
                # Update the chunk
                fixed_chunk['page_start'] = page_start
                fixed_chunk['page_end'] = page_end
                
                # Add some debugging info
                fixed_chunk['_original_page_info'] = {
                    'page_range': chunk.get('page_range'),
                    'page': chunk.get('page'),
                    'parsed_start': page_start,
                    'parsed_end': page_end
                }
                
                fixed_chunks.append(fixed_chunk)
            
            result['chunks'] = fixed_chunks
        
        return result
    
    def get_detailed_output(self, pdf_path: str) -> Dict[str, Any]:
        """Get detailed output with analysis."""
        result = self.extract_fire_sections(pdf_path)
        
        analysis = {
            'pdf_name': Path(pdf_path).name,
            'extraction_method': result.get('extraction_method'),
            'toc_found': result.get('toc_found'),
            'total_chunks': len(result.get('chunks', [])),
            'chunks_with_pages': 0,
            'chunks_without_pages': 0,
            'page_ranges': [],
            'chunks': []
        }
        
        # Analyze chunks
        for i, chunk in enumerate(result.get('chunks', []), 1):
            chunk_info = {
                'index': i,
                'page_start': chunk.get('page_start'),
                'page_end': chunk.get('page_end'),
                'text_length': len(chunk.get('text', '')),
                'text_preview': chunk.get('text', '')[:150].replace('\n', ' '),
                'section_title': chunk.get('section_title', ''),
                'extraction_method': chunk.get('extraction_method', ''),
                'confidence': chunk.get('confidence', ''),
                'original_page_info': chunk.get('_original_page_info', {})
            }
            
            if chunk.get('page_start') is not None:
                analysis['chunks_with_pages'] += 1
                analysis['page_ranges'].append(f"{chunk['page_start']}-{chunk['page_end']}")
            else:
                analysis['chunks_without_pages'] += 1
                
            analysis['chunks'].append(chunk_info)
        
        return analysis

def test_fixed_parser():
    """Test the fixed parser on sample PDFs."""
    specs_dir = Path(__file__).parent.parent / "specs"
    test_pdfs = [
        "Ohio_Cincinnati_Addendum.pdf",
        "NYC_HPD_Table_of_Contents.pdf", 
        "3670 Specifications DAFS.pdf"
    ]
    
    parser = FixedTOCParser()
    
    for pdf_name in test_pdfs:
        pdf_path = specs_dir / pdf_name
        if not pdf_path.exists():
            print(f"⚠️  Skipping missing file: {pdf_name}")
            continue
            
        print(f"\n🔍 TESTING: {pdf_name}")
        print("=" * 60)
        
        try:
            analysis = parser.get_detailed_output(str(pdf_path))
            
            print(f"📊 SUMMARY:")
            print(f"  Method: {analysis['extraction_method']}")
            print(f"  TOC Found: {analysis['toc_found']}")
            print(f"  Total chunks: {analysis['total_chunks']}")
            print(f"  Chunks with pages: {analysis['chunks_with_pages']}")
            print(f"  Chunks without pages: {analysis['chunks_without_pages']}")
            
            if analysis['page_ranges']:
                print(f"  Page ranges: {', '.join(analysis['page_ranges'])}")
            
            print(f"\n📄 CHUNKS:")
            for chunk in analysis['chunks'][:3]:  # Show first 3
                pages = f"{chunk['page_start']}-{chunk['page_end']}" if chunk['page_start'] else "No pages"
                print(f"  {chunk['index']}. Pages {pages} ({chunk['text_length']} chars)")
                print(f"     {chunk['text_preview']}...")
                if chunk['section_title']:
                    print(f"     Section: {chunk['section_title']}")
                
                # Show original page info for debugging
                orig = chunk['original_page_info']
                if orig:
                    print(f"     Debug: page_range={orig.get('page_range')}, page={orig.get('page')}")
                print()
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_fixed_parser() 
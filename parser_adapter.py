#!/usr/bin/env python3
"""
Parser Adapter - Connects custom parsers to Grail test suite interface.

This adapter bridges the gap between the user's custom parsers and the
standard interface expected by the Grail test suite.
"""
import sys
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, NamedTuple, Optional
from parser import ParseResult  # Import from the existing grail parser

# Add parsers directory to Python path
PARSERS_DIR = Path(__file__).parent / "parsers"
sys.path.insert(0, str(PARSERS_DIR))


class ParseResult(NamedTuple):
    """Standard result format for Grail test suite."""
    chunks: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]


class CustomParserAdapter:
    """Adapter for custom PDF parsers to work with Grail test suite."""
    
    def __init__(self, parser_name: str = "toc_driven_chunker"):
        """
        Initialize adapter with a specific parser.
        
        Args:
            parser_name: Name of the parser module to use
                       Options: "toc_driven_chunker", "production_chunker", "page_scoring"
        """
        self.parser_name = parser_name
        self.parser_module = None
        self.chunker = None
        self._load_parser()
    
    def _load_parser(self):
        """Load the specified parser module."""
        try:
            pyc_file = PARSERS_DIR / f"{self.parser_name}.cpython-313.pyc"
            if not pyc_file.exists():
                raise FileNotFoundError(f"Parser file not found: {pyc_file}")
            
            spec = importlib.util.spec_from_file_location(self.parser_name, str(pyc_file))
            if not spec or not spec.loader:
                raise ImportError(f"Could not create spec for {self.parser_name}")
            
            self.parser_module = importlib.util.module_from_spec(spec)
            sys.modules[self.parser_name] = self.parser_module
            spec.loader.exec_module(self.parser_module)
            
            # Initialize the appropriate chunker class
            if self.parser_name == "toc_driven_chunker":
                self.chunker = self.parser_module.TOCDrivenChunker()
            elif self.parser_name == "production_chunker":
                self.chunker = self.parser_module.ProductionSpecChunker()
            elif self.parser_name == "page_scoring":
                self.chunker = self.parser_module.PageScorer()
            elif self.parser_name == "section_stitcher":
                self.chunker = self.parser_module.SectionStitcher()
            else:
                raise ValueError(f"Unknown parser: {self.parser_name}")
            
            print(f"✓ Loaded parser: {self.parser_name}")
            
        except Exception as e:
            print(f"✗ Failed to load parser {self.parser_name}: {e}")
            raise
    
    def parse_pdf(self, pdf_path: str) -> ParseResult:
        """
        Parse PDF using the custom parser and convert to standard format.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            ParseResult with standardized chunks and entities
        """
        if not self.chunker:
            raise RuntimeError(f"Parser {self.parser_name} not loaded")
        
        try:
            # Call the parser's extract method
            raw_result = self.chunker.extract_fire_sections(pdf_path)
            
            # Convert to standard format
            chunks = self._convert_chunks(raw_result)
            entities = self._extract_entities(raw_result)
            
            return ParseResult(chunks=chunks, entities=entities)
            
        except Exception as e:
            print(f"✗ Error parsing {pdf_path} with {self.parser_name}: {e}")
            # Return empty result on failure
            return ParseResult(chunks=[], entities=[])
    
    def _convert_chunks(self, raw_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert parser-specific chunk format to standard format.
        
        Args:
            raw_result: Raw result from custom parser
            
        Returns:
            List of standardized chunk dictionaries
        """
        chunks = []
        
        if self.parser_name == "toc_driven_chunker":
            # TOC chunker returns: {'chunks': [{'text': '...', 'page': N, ...}]}
            if 'chunks' in raw_result:
                for i, chunk_data in enumerate(raw_result['chunks']):
                    chunk = {
                        'title': self._extract_title_from_text(chunk_data.get('text', '')),
                        'start_page': chunk_data.get('page', 1),
                        'end_page': chunk_data.get('page', 1),  # Single page for now
                        'confidence': chunk_data.get('confidence', 'medium'),
                        'extraction_method': chunk_data.get('extraction_method', 'unknown')
                    }
                    chunks.append(chunk)
        
        elif self.parser_name == "production_chunker":
            # Production chunker returns: {'primary_content': [...], 'secondary_content': [...]}
            for content_type in ['primary_content', 'secondary_content']:
                if content_type in raw_result:
                    for i, chunk_data in enumerate(raw_result[content_type]):
                        chunk = {
                            'title': chunk_data.get('title', f'{content_type.title()} Section {i+1}'),
                            'start_page': chunk_data.get('start_page', 1),
                            'end_page': chunk_data.get('end_page', 1),
                            'content_type': content_type
                        }
                        chunks.append(chunk)
        
        # If no chunks found, create a default chunk
        if not chunks:
            chunks = [{
                'title': f'Document processed by {self.parser_name}',
                'start_page': 1,
                'end_page': 1,
                'note': 'No specific sections identified'
            }]
        
        return chunks
    
    def _extract_title_from_text(self, text: str) -> str:
        """Extract a meaningful title from chunk text."""
        if not text:
            return "Unnamed Section"
        
        # Take first line or first 50 characters
        lines = text.strip().split('\n')
        first_line = lines[0].strip()
        
        # Clean up and truncate
        if len(first_line) > 50:
            first_line = first_line[:47] + "..."
        
        return first_line if first_line else "Unnamed Section"
    
    def _extract_entities(self, raw_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract fire protection entities from the raw result.
        
        Args:
            raw_result: Raw result from custom parser
            
        Returns:
            List of entity dictionaries
        """
        entities = []
        
        # For now, create mock entities based on the chunks found
        # This could be enhanced to actually extract pipe specs, etc.
        if self.parser_name == "toc_driven_chunker" and 'chunks' in raw_result:
            for i, chunk in enumerate(raw_result['chunks']):
                text = chunk.get('text', '')
                
                # Look for fire suppression related content
                if 'FIRE SUPPRESSION' in text.upper() or 'SPRINKLER' in text.upper():
                    entity = {
                        'id': f'fire_system_{i:03d}',
                        'type': 'fire_suppression_system',
                        'description': self._extract_title_from_text(text),
                        'location_page': chunk.get('page', 1),
                        'source_parser': self.parser_name
                    }
                    entities.append(entity)
        
        return entities


# Create different parser instances
def get_toc_parser():
    """Get TOC-driven parser instance."""
    return CustomParserAdapter("toc_driven_chunker")

def get_production_parser():
    """Get production spec parser instance.""" 
    return CustomParserAdapter("production_chunker")

def get_page_scoring_parser():
    """Get page scoring parser instance."""
    return CustomParserAdapter("page_scoring")


# Override the main parse_pdf function to use custom parser
def parse_pdf(pdf_path: str) -> ParseResult:
    """
    Main parse_pdf function that uses the custom parser.
    
    This replaces the mock parser in the original grail-test-suite.
    """
    # Use TOC-driven parser by default (showed best results)
    adapter = get_toc_parser()
    return adapter.parse_pdf(pdf_path)


if __name__ == "__main__":
    # Test the adapter
    test_pdf = "specs/NYC_HPD_Table_of_Contents.pdf"
    
    print("=== Testing Custom Parser Adapter ===")
    
    for parser_name in ["toc_driven_chunker", "production_chunker"]:
        print(f"\n--- Testing {parser_name} ---")
        try:
            adapter = CustomParserAdapter(parser_name)
            result = adapter.parse_pdf(test_pdf)
            
            print(f"✓ {parser_name}: {len(result.chunks)} chunks, {len(result.entities)} entities")
            for i, chunk in enumerate(result.chunks):
                print(f"  Chunk {i+1}: {chunk['title']} (pages {chunk['start_page']}-{chunk['end_page']})")
                
        except Exception as e:
            print(f"✗ {parser_name} failed: {e}") 
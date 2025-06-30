"""
Ground truth data generation tool for PDF specifications.

This tool helps create and manage ground truth data files (.fire.json) 
for testing PDF parsing accuracy.
"""
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import time
from parser import parse_pdf


@dataclass
class GroundTruthMetadata:
    """Metadata for ground truth data."""
    pdf_name: str
    pdf_size_mb: float
    total_pages: int
    generation_date: str
    parser_version: str
    manual_validation: bool = False
    notes: str = ""


@dataclass
class GroundTruthData:
    """Complete ground truth data structure."""
    metadata: GroundTruthMetadata
    chunks: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]
    stats: Dict[str, Any]


class GroundTruthGenerator:
    """Generate and manage ground truth data for PDF specifications."""
    
    def __init__(self, specs_dir: Path, output_dir: Optional[Path] = None):
        self.specs_dir = specs_dir
        self.output_dir = output_dir or specs_dir
        
    def generate_from_pdf(self, pdf_path: Path, 
                         manual_review: bool = False,
                         overwrite: bool = False) -> Path:
        """
        Generate ground truth data from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            manual_review: Whether to prompt for manual review/editing
            overwrite: Whether to overwrite existing ground truth files
            
        Returns:
            Path to generated .fire.json file
        """
        print(f"Generating ground truth for: {pdf_path.name}")
        
        # Check if output already exists
        output_path = self.output_dir / f"{pdf_path.stem}.fire.json"
        if output_path.exists() and not overwrite:
            print(f"Ground truth already exists: {output_path}")
            print("Use --overwrite to regenerate")
            return output_path
        
        # Parse PDF to get initial data
        start_time = time.time()
        parse_result = parse_pdf(str(pdf_path))
        parse_time = time.time() - start_time
        
        # Create metadata
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        metadata = GroundTruthMetadata(
            pdf_name=pdf_path.name,
            pdf_size_mb=round(file_size_mb, 2),
            total_pages=getattr(parse_result, 'total_pages', 0),
            generation_date=time.strftime("%Y-%m-%d %H:%M:%S"),
            parser_version="1.0.0",  # TODO: Get from parser module
            manual_validation=manual_review
        )
        
        # Extract chunks and entities
        chunks = getattr(parse_result, 'chunks', [])
        entities = getattr(parse_result, 'entities', [])
        
        # Create stats
        stats = {
            'total_chunks': len(chunks),
            'total_entities': len(entities),
            'parse_time_seconds': round(parse_time, 2),
            'throughput_mb_per_sec': round(file_size_mb / parse_time, 2) if parse_time > 0 else 0
        }
        
        # Create ground truth data
        ground_truth = GroundTruthData(
            metadata=metadata,
            chunks=chunks,
            entities=entities,
            stats=stats
        )
        
        # Manual review if requested
        if manual_review:
            ground_truth = self._manual_review(ground_truth)
        
        # Save to file
        self._save_ground_truth(ground_truth, output_path)
        
        print(f"✓ Generated ground truth: {output_path}")
        print(f"  - {len(chunks)} chunks, {len(entities)} entities")
        print(f"  - Parse time: {parse_time:.2f}s")
        
        return output_path
    
    def _manual_review(self, ground_truth: GroundTruthData) -> GroundTruthData:
        """Prompt user for manual review and editing of ground truth data."""
        print("\n=== MANUAL REVIEW ===")
        print(f"PDF: {ground_truth.metadata.pdf_name}")
        print(f"Chunks found: {len(ground_truth.chunks)}")
        print(f"Entities found: {len(ground_truth.entities)}")
        
        # Review chunks
        print("\nChunk review:")
        for i, chunk in enumerate(ground_truth.chunks):
            print(f"  {i+1}. {chunk.get('title', 'No title')} "
                  f"(pages {chunk.get('start_page', '?')}-{chunk.get('end_page', '?')})")
        
        # Ask for corrections
        while True:
            action = input("\nActions: (c)ontinue, (e)dit chunks, (a)dd notes, (q)uit: ").lower()
            
            if action == 'c':
                break
            elif action == 'e':
                ground_truth = self._edit_chunks_interactive(ground_truth)
            elif action == 'a':
                notes = input("Add notes: ")
                ground_truth.metadata.notes = notes
            elif action == 'q':
                print("Aborting ground truth generation")
                sys.exit(0)
            else:
                print("Invalid action")
        
        ground_truth.metadata.manual_validation = True
        return ground_truth
    
    def _edit_chunks_interactive(self, ground_truth: GroundTruthData) -> GroundTruthData:
        """Interactive chunk editing."""
        print("\nChunk editing (simple implementation):")
        print("This is a basic implementation. For complex editing, modify the .fire.json file directly.")
        
        # Allow user to remove chunks
        to_remove = input("Enter chunk numbers to remove (comma-separated, 1-based): ")
        if to_remove.strip():
            try:
                indices = [int(x.strip()) - 1 for x in to_remove.split(',')]
                indices = sorted(indices, reverse=True)  # Remove from end to preserve indices
                for idx in indices:
                    if 0 <= idx < len(ground_truth.chunks):
                        removed = ground_truth.chunks.pop(idx)
                        print(f"Removed chunk: {removed.get('title', 'No title')}")
            except ValueError:
                print("Invalid input format")
        
        return ground_truth
    
    def _save_ground_truth(self, ground_truth: GroundTruthData, output_path: Path):
        """Save ground truth data to JSON file."""
        # Convert to dictionary and save
        data = asdict(ground_truth)
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def batch_generate(self, pattern: str = "*.pdf", 
                      manual_review: bool = False,
                      overwrite: bool = False) -> List[Path]:
        """
        Generate ground truth data for multiple PDFs.
        
        Args:
            pattern: Glob pattern for PDF files
            manual_review: Whether to prompt for manual review
            overwrite: Whether to overwrite existing files
            
        Returns:
            List of generated .fire.json file paths
        """
        pdf_files = list(self.specs_dir.glob(pattern))
        print(f"Found {len(pdf_files)} PDF files matching '{pattern}'")
        
        generated_files = []
        
        for pdf_path in pdf_files:
            try:
                output_path = self.generate_from_pdf(
                    pdf_path, 
                    manual_review=manual_review,
                    overwrite=overwrite
                )
                generated_files.append(output_path)
            except Exception as e:
                print(f"Error processing {pdf_path.name}: {e}")
                continue
        
        print(f"\n✓ Generated {len(generated_files)} ground truth files")
        return generated_files
    
    def validate_existing(self) -> Dict[str, Any]:
        """Validate all existing ground truth files in the specs directory."""
        json_files = list(self.specs_dir.glob("*.fire.json"))
        results = {
            'total_files': len(json_files),
            'valid_files': 0,
            'invalid_files': [],
            'missing_pdfs': []
        }
        
        for json_path in json_files:
            try:
                # Check if corresponding PDF exists
                pdf_path = json_path.with_suffix('.pdf')
                if not pdf_path.exists():
                    results['missing_pdfs'].append(json_path.name)
                    continue
                
                # Validate JSON structure
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                # Basic validation
                required_keys = ['chunks']  # Minimal requirement
                if all(key in data for key in required_keys):
                    results['valid_files'] += 1
                else:
                    results['invalid_files'].append(json_path.name)
                    
            except Exception as e:
                results['invalid_files'].append(f"{json_path.name}: {e}")
        
        return results


def main():
    """Command-line interface for ground truth generation."""
    parser = argparse.ArgumentParser(description="Generate ground truth data for PDF specifications")
    parser.add_argument("--specs-dir", type=Path, default=Path("specs"),
                       help="Directory containing PDF specifications")
    parser.add_argument("--output-dir", type=Path,
                       help="Output directory for .fire.json files (default: same as specs-dir)")
    parser.add_argument("--pdf", type=str,
                       help="Generate ground truth for specific PDF file")
    parser.add_argument("--batch", action="store_true",
                       help="Generate ground truth for all PDFs")
    parser.add_argument("--pattern", type=str, default="*.pdf",
                       help="Glob pattern for batch processing")
    parser.add_argument("--manual-review", action="store_true",
                       help="Enable manual review and editing")
    parser.add_argument("--overwrite", action="store_true",
                       help="Overwrite existing ground truth files")
    parser.add_argument("--validate", action="store_true",
                       help="Validate existing ground truth files")
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = GroundTruthGenerator(args.specs_dir, args.output_dir)
    
    if args.validate:
        # Validate existing files
        results = generator.validate_existing()
        print(f"Validation Results:")
        print(f"  Total files: {results['total_files']}")
        print(f"  Valid files: {results['valid_files']}")
        if results['invalid_files']:
            print(f"  Invalid files: {results['invalid_files']}")
        if results['missing_pdfs']:
            print(f"  Missing PDFs: {results['missing_pdfs']}")
        
    elif args.pdf:
        # Generate for specific PDF
        pdf_path = args.specs_dir / args.pdf
        if not pdf_path.exists():
            print(f"Error: PDF file not found: {pdf_path}")
            sys.exit(1)
        
        generator.generate_from_pdf(
            pdf_path,
            manual_review=args.manual_review,
            overwrite=args.overwrite
        )
        
    elif args.batch:
        # Batch generation
        generator.batch_generate(
            pattern=args.pattern,
            manual_review=args.manual_review,
            overwrite=args.overwrite
        )
        
    else:
        print("Please specify --pdf, --batch, or --validate")
        parser.print_help()


if __name__ == "__main__":
    main() 
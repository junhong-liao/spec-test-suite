"""
Test configuration module for managing test parameters and settings.

This module centralizes all test configuration to make it easy to adjust
thresholds and parameters as the test suite scales to 50-100+ examples.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PerformanceThresholds:
    """Performance thresholds for different test scenarios."""
    # Realistic thresholds for actual PDF parsing (not mock data)
    base_time_seconds: float = 5.0  # Real PDF parsing has overhead
    time_per_mb_seconds: float = 2.0  # 2 seconds per MB is realistic for OCR/text extraction
    max_time_seconds: float = 120.0  # 2 minute cap for very large documents
    min_throughput_mb_per_sec: float = 0.5  # 0.5 MB/s minimum (much more realistic)
    
    # Memory thresholds
    max_memory_mb: float = 2000.0  # Higher memory usage for real parsing
    memory_per_mb_input: float = 100.0  # More memory per MB for complex processing


@dataclass
class AccuracyThresholds:
    """Accuracy thresholds for different types of documents."""
    # Chunk accuracy
    chunk_iou_threshold: float = 0.7
    chunk_page_tolerance: int = 2
    fuzzy_title_matching: bool = True
    
    # Entity accuracy
    entity_precision_threshold: float = 0.9
    entity_recall_threshold: float = 0.9
    entity_f1_threshold: float = 0.9
    
    # Edge case handling (lower thresholds for complex documents)
    edge_case_precision_threshold: float = 0.85
    edge_case_recall_threshold: float = 0.85


@dataclass
class DocumentTypeConfig:
    """Configuration for different document types."""
    name: str
    min_chunks: int
    max_chunks: int
    performance_multiplier: float = 1.0
    accuracy_thresholds: Optional[AccuracyThresholds] = None
    
    def __post_init__(self):
        if self.accuracy_thresholds is None:
            self.accuracy_thresholds = AccuracyThresholds()


class TestConfig:
    """Central test configuration manager."""
    
    def __init__(self):
        self.performance = PerformanceThresholds()
        self.accuracy = AccuracyThresholds()
        self._document_types = self._initialize_document_types()
        self._load_environment_overrides()
    
    def _initialize_document_types(self) -> Dict[str, DocumentTypeConfig]:
        """Initialize configuration for different document types."""
        return {
            'table_of_contents': DocumentTypeConfig(
                name='Table of Contents',
                min_chunks=3,  # TOCs typically have multiple sections
                max_chunks=20,  # Can be quite detailed
                performance_multiplier=0.8,  # Usually faster to parse (less complex)
            ),
            'addendum': DocumentTypeConfig(
                name='Addendum',
                min_chunks=5,  # Addendums have multiple sections
                max_chunks=25,  # Can be substantial documents
                performance_multiplier=1.0,
            ),
            'manual': DocumentTypeConfig(
                name='Project Manual',
                min_chunks=15,  # Project manuals are comprehensive
                max_chunks=100,  # Large manuals can have many sections
                performance_multiplier=1.8,  # Larger, more complex documents
            ),
            'specification': DocumentTypeConfig(
                name='Specification',
                min_chunks=8,  # Specs have detailed sections
                max_chunks=50,  # Technical specifications can be extensive
                performance_multiplier=1.4,  # Technical content is slower to parse
            ),
            'stress_test': DocumentTypeConfig(
                name='OCR Stress Test',
                min_chunks=5,  # OCR documents still have structure
                max_chunks=30,  # But may not parse as cleanly
                performance_multiplier=4.0,  # OCR documents are much slower
                accuracy_thresholds=AccuracyThresholds(
                    entity_precision_threshold=0.6,  # Lower expectations for OCR
                    entity_recall_threshold=0.6,
                    chunk_iou_threshold=0.5,  # OCR may have poor chunking
                    edge_case_precision_threshold=0.5,
                    edge_case_recall_threshold=0.5
                )
            ),
            'default': DocumentTypeConfig(
                name='Default',
                min_chunks=5,  # Most documents have some structure
                max_chunks=40,  # Reasonable upper bound for unknown docs
                performance_multiplier=1.2,  # Conservative estimate
            )
        }
    
    def _load_environment_overrides(self):
        """Load configuration overrides from environment variables."""
        # Performance overrides
        if os.getenv('TEST_MAX_TIME_SECONDS'):
            self.performance.max_time_seconds = float(os.getenv('TEST_MAX_TIME_SECONDS'))
        
        if os.getenv('TEST_MIN_THROUGHPUT'):
            self.performance.min_throughput_mb_per_sec = float(os.getenv('TEST_MIN_THROUGHPUT'))
        
        # Accuracy overrides
        if os.getenv('TEST_ENTITY_PRECISION_THRESHOLD'):
            self.accuracy.entity_precision_threshold = float(os.getenv('TEST_ENTITY_PRECISION_THRESHOLD'))
        
        if os.getenv('TEST_ENTITY_RECALL_THRESHOLD'):
            self.accuracy.entity_recall_threshold = float(os.getenv('TEST_ENTITY_RECALL_THRESHOLD'))
    
    def get_document_type_config(self, filename: str) -> DocumentTypeConfig:
        """
        Get configuration for a document based on filename patterns.
        
        Args:
            filename: Name of the document file
            
        Returns:
            DocumentTypeConfig appropriate for the document type
        """
        filename_lower = filename.lower()
        
        # Pattern matching for document types
        if 'table_of_contents' in filename_lower or 'toc' in filename_lower or 'contents' in filename_lower or filename_lower.endswith('_toc.pdf') or 'index' in filename_lower:
            return self._document_types['table_of_contents']
        elif 'addendum' in filename_lower or 'addenda' in filename_lower or 'appendix' in filename_lower:
            return self._document_types['addendum']
        elif 'manual' in filename_lower:
            return self._document_types['manual']
        elif 'stress_test' in filename_lower or 'ocr' in filename_lower:
            return self._document_types['stress_test']
        elif any(spec_term in filename_lower for spec_term in ['spec', 'division', 'section']):
            return self._document_types['specification']
        else:
            return self._document_types['default']
    
    def get_performance_threshold(self, file_size_mb: float, document_type: str = 'default') -> float:
        """
        Calculate performance threshold for a document.
        
        Args:
            file_size_mb: File size in megabytes
            document_type: Type of document (for multiplier)
            
        Returns:
            Maximum allowed processing time in seconds
        """
        config = self._document_types.get(document_type, self._document_types['default'])
        
        base_time = self.performance.base_time_seconds
        size_time = file_size_mb * self.performance.time_per_mb_seconds
        multiplier = config.performance_multiplier
        
        calculated_time = (base_time + size_time) * multiplier
        
        return min(calculated_time, self.performance.max_time_seconds)
    
    def should_run_full_validation(self) -> bool:
        """Determine if full validation should be run based on environment."""
        # Skip expensive tests in CI by default
        if os.getenv('CI') == 'true':
            return os.getenv('RUN_FULL_VALIDATION') == 'true'
        return True
    
    def get_test_subset_size(self) -> Optional[int]:
        """Get the number of tests to run in subset mode."""
        subset_size = os.getenv('TEST_SUBSET_SIZE')
        return int(subset_size) if subset_size else None
    
    def is_parallel_testing_enabled(self) -> bool:
        """Check if parallel testing is enabled."""
        return os.getenv('DISABLE_PARALLEL_TESTS') != 'true'
    
    def get_log_level(self) -> str:
        """Get logging level for tests."""
        return os.getenv('TEST_LOG_LEVEL', 'INFO')
    
    def export_for_ci(self) -> Dict[str, Any]:
        """Export configuration suitable for CI environment variables."""
        return {
            'TEST_MAX_TIME_SECONDS': self.performance.max_time_seconds,
            'TEST_MIN_THROUGHPUT': self.performance.min_throughput_mb_per_sec,
            'TEST_ENTITY_PRECISION_THRESHOLD': self.accuracy.entity_precision_threshold,
            'TEST_ENTITY_RECALL_THRESHOLD': self.accuracy.entity_recall_threshold,
            'TEST_CHUNK_IOU_THRESHOLD': self.accuracy.chunk_iou_threshold,
        }


# Global configuration instance
test_config = TestConfig()


# Convenience functions for common operations
def get_thresholds_for_file(file_path: Path) -> tuple[float, DocumentTypeConfig]:
    """
    Get performance threshold and document config for a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Tuple of (performance_threshold_seconds, document_config)
    """
    file_size_mb = file_path.stat().st_size / (1024 * 1024) if file_path.exists() else 1.0
    doc_config = test_config.get_document_type_config(file_path.name)
    
    # Use document type for threshold calculation
    doc_type_key = None
    for key, config in test_config._document_types.items():
        if config.name == doc_config.name:
            doc_type_key = key
            break
    
    threshold = test_config.get_performance_threshold(file_size_mb, doc_type_key or 'default')
    
    return threshold, doc_config


def should_skip_slow_tests() -> bool:
    """Check if slow tests should be skipped."""
    return os.getenv('SKIP_SLOW_TESTS') == 'true'


def get_test_timeout() -> float:
    """Get timeout for individual tests."""
    return float(os.getenv('TEST_TIMEOUT_SECONDS', str(test_config.performance.max_time_seconds * 2)))


# Export commonly used configurations
__all__ = [
    'TestConfig',
    'PerformanceThresholds', 
    'AccuracyThresholds',
    'DocumentTypeConfig',
    'test_config',
    'get_thresholds_for_file',
    'should_skip_slow_tests',
    'get_test_timeout'
] 
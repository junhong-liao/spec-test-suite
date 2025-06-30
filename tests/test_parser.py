"""
Main test functions for parser validation.
"""
import json
import pytest
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
from parser import parse_pdf, DocumentChunker, parse_pdf_real
from tests.utils import compare_chunks, score_entities


# Test case configurations
TEST_CASES = [
    {
        "id": "gold_001",
        "description": "Basic fire piping system",
        "expected_chunks": 2,
        "expected_entities": 1,
        "min_precision": 0.9,
        "min_recall": 0.9
    },
    {
        "id": "gold_002", 
        "description": "Multi-floor commercial building",
        "expected_chunks": 6,
        "expected_entities": 5,
        "min_precision": 0.9,
        "min_recall": 0.9
    },
    {
        "id": "gold_003",
        "description": "Edge cases and special materials",
        "expected_chunks": 3,
        "expected_entities": 4,
        "min_precision": 0.85,  # Lower threshold for edge cases
        "min_recall": 0.85
    },
    {
        "id": "gold_004",
        "description": "Large commercial complex",
        "expected_chunks": 6,
        "expected_entities": 8,
        "min_precision": 0.9,
        "min_recall": 0.9
    },
    {
        "id": "gold_005",
        "description": "Mixed materials system",
        "expected_chunks": 5,
        "expected_entities": 6,
        "min_precision": 0.9,
        "min_recall": 0.9
    }
]


def load_test_data(test_case_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Load ground truth data for a test case.
    
    Args:
        test_case_id: ID of the test case (e.g., 'gold_001')
        
    Returns:
        Tuple of (chunks, entities) ground truth data
    """
    test_dir = Path(__file__).parent / "fire_piping" / test_case_id
    
    with open(test_dir / "chunks.json", 'r') as f:
        chunks = json.load(f)
    
    with open(test_dir / "entities.json", 'r') as f:
        entities = json.load(f)
    
    return chunks, entities


def time_parser_execution(pdf_path: str) -> Tuple[Any, float]:
    """
    Time the parser execution and return results with timing.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Tuple of (parse_result, execution_time_seconds)
    """
    start_time = time.time()
    result = parse_pdf(pdf_path)
    execution_time = time.time() - start_time
    return result, execution_time


@pytest.mark.parametrize("test_case", TEST_CASES)
@pytest.mark.smoke
def test_all_chunking_cases(test_case: Dict[str, Any]):
    """Test chunking accuracy for all test cases."""
    test_case_id = test_case["id"]
    
    # Load test data
    test_dir = Path(__file__).parent / "fire_piping" / test_case_id
    pdf_path = test_dir / "input.pdf"
    gold_chunks, _ = load_test_data(test_case_id)
    
    # Parse PDF with timing
    result, execution_time = time_parser_execution(str(pdf_path))
    predicted_chunks = result.chunks
    
    # Validate chunk count
    assert len(predicted_chunks) == test_case["expected_chunks"], \
        f"{test_case_id}: Expected {test_case['expected_chunks']} chunks, got {len(predicted_chunks)}"
    
    # Compare chunks
    assert compare_chunks(predicted_chunks, gold_chunks, page_tolerance=1), \
        f"{test_case_id}: Chunks don't match. Predicted: {predicted_chunks}, Gold: {gold_chunks}"
    
    # Performance check (should be fast for mock parser)
    assert execution_time < 1.0, f"{test_case_id}: Parser took too long: {execution_time:.3f}s"
    
    print(f"✓ {test_case_id} chunking: {execution_time:.3f}s")


@pytest.mark.parametrize("test_case", TEST_CASES)
@pytest.mark.smoke  
def test_all_entity_cases(test_case: Dict[str, Any]):
    """Test entity extraction accuracy for all test cases."""
    test_case_id = test_case["id"]
    
    # Load test data
    test_dir = Path(__file__).parent / "fire_piping" / test_case_id
    pdf_path = test_dir / "input.pdf"
    _, gold_entities = load_test_data(test_case_id)
    
    # Parse PDF with timing
    result, execution_time = time_parser_execution(str(pdf_path))
    predicted_entities = result.entities
    
    # Validate entity count
    assert len(predicted_entities) == test_case["expected_entities"], \
        f"{test_case_id}: Expected {test_case['expected_entities']} entities, got {len(predicted_entities)}"
    
    # Score entities
    precision, recall, f1 = score_entities(predicted_entities, gold_entities)
    
    # Assert thresholds (use case-specific thresholds)
    min_precision = test_case["min_precision"]
    min_recall = test_case["min_recall"]
    
    assert precision >= min_precision, \
        f"{test_case_id}: Precision {precision:.3f} below threshold {min_precision}"
    assert recall >= min_recall, \
        f"{test_case_id}: Recall {recall:.3f} below threshold {min_recall}"
    
    print(f"✓ {test_case_id} entities: P={precision:.3f} R={recall:.3f} F1={f1:.3f} ({execution_time:.3f}s)")


@pytest.mark.integration
def test_fuzzy_title_matching():
    """Test fuzzy title matching functionality."""
    from tests.utils import fuzzy_title_match
    
    # Test cases: (title1, title2, should_match)
    test_cases = [
        ("Fire Piping System", "Fire Piping System", True),  # Exact match
        ("Fire Piping System", "fire piping system", True),  # Case difference
        ("Fire Piping System", "Fire Piping Systems", True),  # Small edit
        ("Fire Piping System", "Fire Protection System", False),  # Too different
        ("Material Specs", "Material Specifications", True),  # Abbreviation
        ("Zone 1 - East Wing", "Zone 1 East Wing", True),  # Punctuation difference
        ("System Overview", "Completely Different", False),  # No match
    ]
    
    for title1, title2, expected in test_cases:
        result = fuzzy_title_match(title1, title2)
        assert result == expected, f"'{title1}' vs '{title2}': expected {expected}, got {result}"


@pytest.mark.integration
def test_chunk_continuity_validation():
    """Test chunk continuity validation."""
    from tests.utils import validate_chunk_continuity
    
    # Valid chunks
    valid_chunks = [
        {"title": "Chapter 1", "start_page": 1, "end_page": 5},
        {"title": "Chapter 2", "start_page": 6, "end_page": 10},
        {"title": "Chapter 3", "start_page": 11, "end_page": 15}
    ]
    is_valid, issues = validate_chunk_continuity(valid_chunks)
    assert is_valid, f"Valid chunks failed validation: {issues}"
    assert len(issues) == 0
    
    # Invalid chunks - start > end
    invalid_chunks1 = [
        {"title": "Bad Chunk", "start_page": 10, "end_page": 5}
    ]
    is_valid, issues = validate_chunk_continuity(invalid_chunks1)
    assert not is_valid
    assert len(issues) > 0
    assert "start_page" in issues[0]
    
    # Overlapping chunks
    overlapping_chunks = [
        {"title": "Chapter 1", "start_page": 1, "end_page": 10},
        {"title": "Chapter 2", "start_page": 8, "end_page": 15}
    ]
    is_valid, issues = validate_chunk_continuity(overlapping_chunks)
    assert not is_valid
    assert any("Overlapping" in issue for issue in issues)


@pytest.mark.integration
def test_advanced_iou_calculation():
    """Test advanced IoU calculation with detailed metrics."""
    from tests.utils import calculate_iou_advanced
    
    chunk1 = {"start_page": 1, "end_page": 5}  # 5 pages
    chunk2 = {"start_page": 3, "end_page": 7}  # 5 pages, 3 pages overlap
    
    iou, metrics = calculate_iou_advanced(chunk1, chunk2)
    
    expected_iou = 3 / 7  # 3 pages intersection, 7 pages union
    assert abs(iou - expected_iou) < 0.001
    
    assert metrics['intersection'] == 3
    assert metrics['union'] == 7
    assert metrics['pred_size'] == 5
    assert metrics['gold_size'] == 5
    assert abs(metrics['size_ratio'] - 1.0) < 0.001
    assert abs(metrics['overlap_percentage'] - 0.6) < 0.001


@pytest.mark.integration
def test_enhanced_chunk_comparison():
    """Test enhanced chunk comparison with fuzzy matching."""
    predicted = [
        {"title": "Fire Piping System Overview", "start_page": 1, "end_page": 3},
        {"title": "Material Specs", "start_page": 4, "end_page": 6}  # Abbreviated title
    ]
    
    gold = [
        {"title": "Fire Piping System Overview", "start_page": 1, "end_page": 3},
        {"title": "Material Specifications", "start_page": 4, "end_page": 6}  # Full title
    ]
    
    # Should match with fuzzy matching
    assert compare_chunks(predicted, gold, use_fuzzy_matching=True)
    
    # Should fail without fuzzy matching
    assert not compare_chunks(predicted, gold, use_fuzzy_matching=False)


@pytest.mark.integration
def test_edge_case_normalization():
    """Test normalization edge cases using gold_003."""
    from tests.utils import normalize_diameter, normalize_material, normalize_entity
    
    # Test edge case data from gold_003
    test_entities = [
        {"material": "stainless steel", "diameter": 1.25},
        {"material": "copper type l", "diameter": 0.75},
        {"material": "pvc schedule 80", "diameter": 2.5}
    ]
    
    for entity in test_entities:
        normalized = normalize_entity(entity)
        
        # Verify material normalization
        assert isinstance(normalized["material"], str)
        assert normalized["material"].islower()
        
        # Verify diameter normalization
        assert isinstance(normalized["diameter"], float)
        assert normalized["diameter"] > 0


@pytest.mark.integration
def test_large_system_performance():
    """Test performance with large system (gold_004)."""
    test_dir = Path(__file__).parent / "fire_piping" / "gold_004"
    pdf_path = test_dir / "input.pdf"
    
    # Time multiple runs to get average
    times = []
    for _ in range(3):
        _, execution_time = time_parser_execution(str(pdf_path))
        times.append(execution_time)
    
    avg_time = sum(times) / len(times)
    
    # Performance requirements for large systems
    assert avg_time < 2.0, f"Large system parsing too slow: {avg_time:.3f}s average"
    
    print(f"✓ Large system performance: {avg_time:.3f}s average over 3 runs")


@pytest.mark.integration  
def test_mixed_materials():
    """Test mixed materials handling (gold_005)."""
    test_dir = Path(__file__).parent / "fire_piping" / "gold_005"
    _, gold_entities = load_test_data("gold_005")
    
    # Verify we have diverse materials
    materials = {entity["material"] for entity in gold_entities}
    expected_materials = {"galvanized steel", "copper type l", "pvc schedule 80", "brass", "stainless steel", "bronze"}
    
    # Should have at least 3 different material types
    assert len(materials) >= 3, f"Not enough material diversity: {materials}"
    
    # Test normalization consistency
    from tests.utils import normalize_material
    normalized_materials = {normalize_material(mat) for mat in materials}
    
    # All should normalize to consistent format
    for mat in normalized_materials:
        assert mat.islower()
        assert not any(char in mat for char in ",.!@#$%^&*()[]{}|\\")


def test_smoke_test_performance():
    """Ensure smoke tests run quickly for CI."""
    start_time = time.time()
    
    # Run just the gold_001 tests (basic smoke test)
    test_case = TEST_CASES[0]  # gold_001
    
    # Test chunking
    test_dir = Path(__file__).parent / "fire_piping" / test_case["id"]
    pdf_path = test_dir / "input.pdf"
    gold_chunks, gold_entities = load_test_data(test_case["id"])
    
    result = parse_pdf(str(pdf_path))
    
    # Quick validation
    assert compare_chunks(result.chunks, gold_chunks)
    precision, recall, f1 = score_entities(result.entities, gold_entities)
    assert precision >= 0.9 and recall >= 0.9
    
    total_time = time.time() - start_time
    
    # Smoke test should complete very quickly
    assert total_time < 0.5, f"Smoke test too slow: {total_time:.3f}s"
    
    print(f"✓ Smoke test completed in {total_time:.3f}s")


# Original individual tests for backward compatibility
@pytest.mark.smoke
def test_gold_001_chunking():
    """Test chunking accuracy for gold_001 test case."""
    test_case = next(tc for tc in TEST_CASES if tc["id"] == "gold_001")
    test_all_chunking_cases(test_case)


@pytest.mark.smoke  
def test_gold_001_entities():
    """Test entity extraction accuracy for gold_001 test case."""
    test_case = next(tc for tc in TEST_CASES if tc["id"] == "gold_001")
    test_all_entity_cases(test_case)


# Utility function tests
def test_normalize_diameter():
    """Test diameter normalization function."""
    from tests.utils import normalize_diameter
    
    assert normalize_diameter("1-1/2\"") == 1.5
    assert normalize_diameter("3/4") == 0.75
    assert normalize_diameter("2 inch") == 2.0
    assert normalize_diameter("4") == 4.0


def test_normalize_material():
    """Test material normalization function."""
    from tests.utils import normalize_material
    
    assert normalize_material("Galvanized Steel") == "galvanized steel"
    assert normalize_material("COPPER, TYPE L") == "copper type l"
    assert normalize_material("PVC-Schedule 40") == "pvc schedule 40"


def test_calculate_iou():
    """Test IoU calculation for page ranges."""
    from tests.utils import calculate_iou
    
    chunk1 = {"start_page": 1, "end_page": 3}
    chunk2 = {"start_page": 2, "end_page": 4}
    
    iou = calculate_iou(chunk1, chunk2)
    assert iou == 2/4  # 2 pages overlap, 4 pages total


def test_entities_match():
    """Test the entity matching function."""
    from tests.utils import entities_match
    
    entity1 = {
        "id": "pipe_001",
        "type": "pipe",
        "material": "galvanized steel",
        "diameter": 2.0,
        "schedule": "40",
        "location_page": 5
    }
    
    entity2 = {
        "id": "pipe_002", 
        "type": "pipe",
        "material": "galvanized steel",
        "diameter": 2.0,
        "schedule": "40",
        "location_page": 5
    }
    
    # Should match despite different IDs
    assert entities_match(entity1, entity2)
    
    # Should not match with different material
    entity3 = entity2.copy()
    entity3["material"] = "copper"
    assert not entities_match(entity1, entity3)


@pytest.mark.integration
def test_document_chunker_text_analysis():
    """Test the DocumentChunker class with real text analysis."""
    chunker = DocumentChunker()
    
    sample_text = """
    FIRE PROTECTION SYSTEM OVERVIEW
    This section covers the overall system design for fire protection.
    
    Chapter 1: Material Specifications
    All pipes shall be galvanized steel schedule 40.
    Main distribution lines: pipe size 4 inch diameter.
    Branch lines: pipe size 2.5 inch diameter.
    
    INSTALLATION REQUIREMENTS
    All fittings must be bronze schedule 40.
    Sprinkler heads shall be brass 0.5 inch diameter.
    
    Section 2: Testing and Commissioning
    System must be tested according to NFPA standards.
    """
    
    # Test chunk extraction
    chunks = chunker.extract_text_chunks(sample_text, total_pages=8)
    assert len(chunks) >= 3  # Should find at least 3 sections
    
    chunk_titles = [chunk['title'] for chunk in chunks]
    assert any('FIRE PROTECTION SYSTEM OVERVIEW' in title for title in chunk_titles)
    assert any('Material Specifications' in title for title in chunk_titles)
    assert any('INSTALLATION REQUIREMENTS' in title for title in chunk_titles)
    
    # Test entity extraction  
    entities = chunker.extract_entities(sample_text)
    assert len(entities) >= 2  # Should find at least 2 pipe entities
    
    # Check that entities have required fields
    for entity in entities:
        assert 'id' in entity
        assert 'type' in entity
        assert 'material' in entity
        assert 'diameter' in entity
        assert 'schedule' in entity
        assert 'location_page' in entity


@pytest.mark.integration
def test_document_chunker_helper_methods():
    """Test the DocumentChunker helper methods."""
    chunker = DocumentChunker()
    
    test_text = "This is galvanized steel schedule 40 pipe with 4 inch diameter specifications."
    
    # Test material extraction
    material = chunker._extract_nearby_material(test_text, 20)  # Position near "galvanized"
    assert "galvanized steel" in material.lower()
    
    # Test schedule extraction
    schedule = chunker._extract_nearby_schedule(test_text, 30)  # Position near "schedule"
    assert schedule == "40"
    
    # Test page estimation
    page = chunker._estimate_page(test_text, len(test_text) // 2)
    assert page >= 1
    assert page <= 10


@pytest.mark.integration
def test_parse_pdf_real_functionality():
    """Test the real PDF parser with actual file processing."""
    # Create a temporary file path that doesn't exist in test directories
    temp_path = "/tmp/test_document.pdf"
    
    # Test with non-existent file
    result = parse_pdf_real(temp_path)
    
    # Should return error result but not crash
    assert len(result.chunks) >= 1
    assert len(result.entities) >= 1
    assert 'Error' in result.chunks[0]['title'] or result.chunks[0]['title'] == 'FIRE PROTECTION SYSTEM OVERVIEW'
    

@pytest.mark.integration
def test_chunker_edge_cases():
    """Test edge cases for the DocumentChunker."""
    chunker = DocumentChunker()
    
    # Test with empty text
    chunks = chunker.extract_text_chunks("", total_pages=1)
    assert len(chunks) == 1
    assert chunks[0]['title'] == 'Unknown Document'
    
    entities = chunker.extract_entities("")
    assert len(entities) == 1
    assert entities[0]['id'] == 'default_001'
    
    # Test with no matching patterns
    no_match_text = "This is just plain text with no fire piping information."
    chunks = chunker.extract_text_chunks(no_match_text)
    assert len(chunks) == 1  # Should get default unknown document
    
    entities = chunker.extract_entities(no_match_text)
    assert len(entities) == 1  # Should get default entity


@pytest.mark.integration
def test_chunker_regex_patterns():
    """Test that regex patterns work correctly."""
    chunker = DocumentChunker()
    
    # Test pipe pattern matching
    test_cases = [
        "pipe size 4 inch",
        "pipe 2.5 inch diameter", 
        "Pipe size 1-1/2 inch",
        "PIPE 6\" DIAMETER"
    ]
    
    for case in test_cases:
        entities = chunker.extract_entities(case)
        assert len(entities) >= 1
        assert entities[0]['type'] == 'pipe'
    
    # Test material pattern matching
    material_cases = [
        "galvanized steel pipe",
        "copper type L tubing",
        "PVC schedule 80 pipe",
        "stainless steel fittings"
    ]
    
    for case in material_cases:
        entities = chunker.extract_entities(f"pipe size 2 inch {case}")
        assert len(entities) >= 1
        material = entities[0]['material']
        assert len(material) > 0
        assert material != 'galvanized steel' or 'galvanized steel' in case 
"""
Utility functions for normalizing and comparing parser outputs.
"""
import re
import json
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
try:
    import jsonschema  # type: ignore
except ModuleNotFoundError:
    jsonschema = None  # type: ignore


def validate_json_data(data: List[Dict[str, Any]], schema_type: str) -> bool:
    """
    Validate JSON data against schema.
    
    Args:
        data: Data to validate
        schema_type: Either 'chunks' or 'entities'
        
    Returns:
        True if validation passes
        
    Raises:
        jsonschema.ValidationError: If validation fails
    """
    schema_path = Path(__file__).parent / "fire_piping" / "schemas" / f"{schema_type}.schema.json"
    
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    
    if jsonschema is None:
        # Skip validation gracefully if jsonschema is unavailable
        import warnings
        warnings.warn("jsonschema not installed; skipping schema validation.")
        return True

    jsonschema.validate(data, schema)
    return True


def calculate_levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Edit distance between strings
    """
    if len(s1) < len(s2):
        return calculate_levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def fuzzy_title_match(title1: str, title2: str, max_distance: int = 3) -> bool:
    """
    Check if two titles match using fuzzy string matching.
    
    Args:
        title1: First title
        title2: Second title
        max_distance: Maximum allowed edit distance
        
    Returns:
        True if titles match within edit distance threshold
    """
    # Normalize titles
    norm1 = title1.lower().strip()
    norm2 = title2.lower().strip()
    
    # Exact match
    if norm1 == norm2:
        return True
    
    # Check if one is a substring/abbreviation of the other
    words1 = norm1.split()
    words2 = norm2.split()
    
    # Check abbreviations and word matching for both directions
    def check_word_similarity(words_a, words_b):
        matches = 0
        for word_a in words_a:
            for word_b in words_b:
                # Check if one word is contained in the other or starts with it
                # Also check if one is an abbreviation of the other (e.g., "specs" vs "specifications")
                if (word_a in word_b or word_b in word_a or 
                    word_b.startswith(word_a) or word_a.startswith(word_b) or
                    (len(word_a) >= 4 and len(word_b) >= 4 and word_a[:4] == word_b[:4])):
                    matches += 1
                    break
        return matches == len(words_a)
    
    # Try both directions
    if check_word_similarity(words1, words2) or check_word_similarity(words2, words1):
        return True
    
    # Calculate edit distance
    distance = calculate_levenshtein_distance(norm1, norm2)
    max_len = max(len(norm1), len(norm2))
    
    # Allow up to max_distance edits or 20% of the longer string, whichever is larger
    threshold = max(max_distance, int(max_len * 0.2))
    
    return distance <= threshold


def validate_chunk_continuity(chunks: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    Validate that chunks have reasonable page continuity.
    
    Args:
        chunks: List of chunk dictionaries
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    if not chunks:
        return True, []
    
    # Sort chunks by start page
    sorted_chunks = sorted(chunks, key=lambda x: x['start_page'])
    
    for i, chunk in enumerate(sorted_chunks):
        start_page = chunk['start_page']
        end_page = chunk['end_page']
        
        # Check that start <= end
        if start_page > end_page:
            issues.append(f"Chunk '{chunk['title']}': start_page ({start_page}) > end_page ({end_page})")
        
        # Check for reasonable gaps between chunks
        if i > 0:
            prev_end = sorted_chunks[i-1]['end_page']
            gap = start_page - prev_end - 1
            
            if gap > 10:  # Large gap between chunks
                issues.append(f"Large gap ({gap} pages) between '{sorted_chunks[i-1]['title']}' and '{chunk['title']}'")
            elif gap < 0:  # Overlapping chunks
                overlap = abs(gap)
                issues.append(f"Overlapping chunks ({overlap} pages): '{sorted_chunks[i-1]['title']}' and '{chunk['title']}'")
    
    return len(issues) == 0, issues


def calculate_iou_advanced(pred_chunk: Dict[str, Any], gold_chunk: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Advanced IoU calculation with detailed metrics.
    
    Args:
        pred_chunk: Predicted chunk with start_page and end_page
        gold_chunk: Gold standard chunk with start_page and end_page
        
    Returns:
        Tuple of (iou_score, detailed_metrics)
    """
    pred_start = normalize_page_number(pred_chunk['start_page'])
    pred_end = normalize_page_number(pred_chunk['end_page'])
    gold_start = normalize_page_number(gold_chunk['start_page'])
    gold_end = normalize_page_number(gold_chunk['end_page'])
    
    # Calculate intersection
    intersection_start = max(pred_start, gold_start)
    intersection_end = min(pred_end, gold_end)
    intersection = max(0, intersection_end - intersection_start + 1)
    
    # Calculate union
    pred_size = pred_end - pred_start + 1
    gold_size = gold_end - gold_start + 1
    union = pred_size + gold_size - intersection
    
    iou = intersection / union if union > 0 else 0.0
    
    # Detailed metrics
    metrics = {
        'iou': iou,
        'intersection': intersection,
        'union': union,
        'pred_size': pred_size,
        'gold_size': gold_size,
        'size_ratio': pred_size / gold_size if gold_size > 0 else 0.0,
        'overlap_percentage': intersection / gold_size if gold_size > 0 else 0.0
    }
    
    return iou, metrics


def normalize_diameter(diameter: str) -> float:
    """
    Normalize diameter string to floating point inches.
    
    Examples:
        "1-1/2\"" -> 1.5
        "2 inch" -> 2.0
        "3/4" -> 0.75
    
    Args:
        diameter: Diameter string to normalize
        
    Returns:
        Normalized diameter in inches
    """
    # Remove quotes and extra whitespace
    diameter = diameter.strip().replace('"', '').replace('inch', '').replace('in', '').strip()
    
    # Handle fractions like "1-1/2" or "3/4"
    if '-' in diameter:
        parts = diameter.split('-')
        whole = float(parts[0])
        frac_parts = parts[1].split('/')
        fraction = float(frac_parts[0]) / float(frac_parts[1])
        return whole + fraction
    elif '/' in diameter:
        frac_parts = diameter.split('/')
        return float(frac_parts[0]) / float(frac_parts[1])
    else:
        return float(diameter)


def normalize_material(material: str) -> str:
    """
    Normalize material string for consistent comparison.
    
    Args:
        material: Material string to normalize
        
    Returns:
        Normalized material string
    """
    # Convert to lowercase and remove extra whitespace/punctuation
    normalized = material.lower().strip()
    # Replace hyphens with spaces, then clean up punctuation
    normalized = normalized.replace('-', ' ')
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def normalize_page_number(page: Any) -> int:
    """
    Normalize page number to integer.
    
    Args:
        page: Page number (int, str, or float)
        
    Returns:
        Normalized page number as integer
    """
    if isinstance(page, str):
        return int(page.strip())
    return int(page)


def calculate_iou(pred_chunk: Dict[str, Any], gold_chunk: Dict[str, Any]) -> float:
    """
    Calculate Intersection over Union (IoU) for page ranges.
    
    Args:
        pred_chunk: Predicted chunk with start_page and end_page
        gold_chunk: Gold standard chunk with start_page and end_page
        
    Returns:
        IoU score between 0 and 1
    """
    iou, _ = calculate_iou_advanced(pred_chunk, gold_chunk)
    return iou


def compare_chunks(predicted: List[Dict[str, Any]], 
                  gold_standard: List[Dict[str, Any]], 
                  page_tolerance: int = 1,
                  iou_threshold: float = 0.7,
                  use_fuzzy_matching: bool = True) -> bool:
    """
    Compare predicted chunks against gold standard with enhanced validation.
    
    Args:
        predicted: List of predicted chunks
        gold_standard: List of gold standard chunks
        page_tolerance: Allowed page number tolerance
        iou_threshold: Minimum IoU threshold for overlap
        use_fuzzy_matching: Whether to use fuzzy title matching
        
    Returns:
        True if chunks match with sufficient overlap
    """
    # Validate input data
    try:
        validate_json_data(predicted, 'chunks')
        validate_json_data(gold_standard, 'chunks')
    except jsonschema.ValidationError as e:
        print(f"JSON validation error: {e}")
        return False
    
    # Check chunk count
    if len(predicted) != len(gold_standard):
        print(f"Chunk count mismatch: predicted {len(predicted)}, expected {len(gold_standard)}")
        return False
    
    # Validate chunk continuity
    pred_valid, pred_issues = validate_chunk_continuity(predicted)
    gold_valid, gold_issues = validate_chunk_continuity(gold_standard)
    
    if not pred_valid:
        print(f"Predicted chunks have continuity issues: {pred_issues}")
    if not gold_valid:
        print(f"Gold standard chunks have continuity issues: {gold_issues}")
    
    # Match chunks
    unmatched_gold = gold_standard.copy()
    match_details = []
    
    for pred_chunk in predicted:
        best_match = None
        best_score = 0.0
        best_metrics = None
        
        for gold_chunk in unmatched_gold:
            # Check title similarity
            if use_fuzzy_matching:
                title_match = fuzzy_title_match(pred_chunk['title'], gold_chunk['title'])
            else:
                title_match = pred_chunk['title'].lower().strip() == gold_chunk['title'].lower().strip()
            
            if title_match:
                # Calculate IoU with detailed metrics
                iou, metrics = calculate_iou_advanced(pred_chunk, gold_chunk)
                
                if iou >= iou_threshold and iou > best_score:
                    best_match = gold_chunk
                    best_score = iou
                    best_metrics = metrics
        
        if best_match:
            unmatched_gold.remove(best_match)
            match_details.append({
                'predicted': pred_chunk['title'],
                'matched': best_match['title'],
                'iou': best_score,
                'metrics': best_metrics
            })
        else:
            print(f"No match found for predicted chunk: '{pred_chunk['title']}'")
            # Print potential matches with low IoU for debugging
            for gold_chunk in gold_standard:
                iou, metrics = calculate_iou_advanced(pred_chunk, gold_chunk)
                title_match = fuzzy_title_match(pred_chunk['title'], gold_chunk['title']) if use_fuzzy_matching else False
                print(f"  vs '{gold_chunk['title']}': IoU={iou:.3f}, title_match={title_match}")
            return False
    
    # Check for unmatched gold chunks
    if unmatched_gold:
        print(f"Unmatched gold chunks: {[chunk['title'] for chunk in unmatched_gold]}")
        return False
    
    # Print match summary for debugging
    for match in match_details:
        print(f"✓ '{match['predicted']}' matched '{match['matched']}' (IoU: {match['iou']:.3f})")
    
    return True


def score_entities(predicted: List[Dict[str, Any]], 
                  gold_standard: List[Dict[str, Any]]) -> Tuple[float, float, float]:
    """
    Calculate precision, recall, and F1 score for entity extraction.
    
    Args:
        predicted: List of predicted entities
        gold_standard: List of gold standard entities
        
    Returns:
        Tuple of (precision, recall, f1_score)
    """
    # Validate input data
    try:
        validate_json_data(predicted, 'entities')
        validate_json_data(gold_standard, 'entities')
    except jsonschema.ValidationError as e:
        print(f"JSON validation error: {e}")
        return 0.0, 0.0, 0.0
    
    if not predicted and not gold_standard:
        return 1.0, 1.0, 1.0
    
    if not predicted:
        return 0.0, 0.0, 0.0
    
    if not gold_standard:
        return 0.0, 0.0, 0.0
    
    # Normalize all entities for comparison
    norm_predicted = [normalize_entity(entity) for entity in predicted]
    norm_gold = [normalize_entity(entity) for entity in gold_standard]
    
    true_positives = 0
    
    # Find matches
    for pred_entity in norm_predicted:
        for gold_entity in norm_gold:
            if entities_match(pred_entity, gold_entity):
                true_positives += 1
                break
    
    precision = true_positives / len(predicted)
    recall = true_positives / len(gold_standard)
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return precision, recall, f1_score


def normalize_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an entity for comparison.
    
    Args:
        entity: Entity dictionary to normalize
        
    Returns:
        Normalized entity dictionary
    """
    normalized = entity.copy()
    
    if 'material' in normalized:
        normalized['material'] = normalize_material(normalized['material'])
    
    if 'diameter' in normalized:
        if isinstance(normalized['diameter'], str):
            normalized['diameter'] = normalize_diameter(normalized['diameter'])
    
    if 'location_page' in normalized:
        normalized['location_page'] = normalize_page_number(normalized['location_page'])
    
    return normalized


def entities_match(entity1: Dict[str, Any], entity2: Dict[str, Any]) -> bool:
    """
    Check if two normalized entities match.
    
    Args:
        entity1: First entity to compare
        entity2: Second entity to compare
        
    Returns:
        True if entities match on key fields
    """
    key_fields = ['type', 'material', 'diameter', 'schedule']
    
    for field in key_fields:
        if field in entity1 and field in entity2:
            if entity1[field] != entity2[field]:
                return False
    
    # Allow ±1 page tolerance for location
    if 'location_page' in entity1 and 'location_page' in entity2:
        page_diff = abs(entity1['location_page'] - entity2['location_page'])
        if page_diff > 1:
            return False
    
    return True 
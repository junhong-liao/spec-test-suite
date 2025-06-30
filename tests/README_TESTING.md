# Robust PDF Parser Testing Infrastructure

This directory contains a comprehensive test infrastructure designed to scale with 50-100+ real-world PDF examples while maintaining test quality and performance.

## Overview

The test infrastructure consists of three main components:

1. **Legacy Tests**: Original hardcoded test cases (`test_parser.py`)
2. **Real-World Tests**: Scalable tests using actual PDFs (`test_real_world_specs.py`)
3. **Ground Truth Generation**: Tools for creating and managing test data (`ground_truth_generator.py`)

## Test Structure

### Legacy Tests (`test_parser.py`)
- Uses hardcoded `gold_001` through `gold_005` test cases
- Fast, deterministic tests for core functionality
- Continues to provide regression testing for basic features

### Real-World Tests (`test_real_world_specs.py`)
- **Automatic Discovery**: Finds all PDFs in `/specs` directory
- **Adaptive Thresholds**: Performance and accuracy thresholds based on document type
- **Ground Truth Integration**: Uses existing `.fire.json` files when available
- **Smoke Tests**: Basic validation for PDFs without ground truth
- **Performance Benchmarks**: Comprehensive performance testing across all specs

### Test Configuration (`test_config.py`)
Centralized configuration for:
- Performance thresholds by document type
- Accuracy requirements (precision, recall, F1)
- Environment-based overrides
- CI/CD optimization settings

## Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest

# Run only smoke tests (fast)
pytest -m smoke

# Run real-world tests
pytest -m real_world

# Run tests with ground truth only
pytest -m ground_truth

# Run performance benchmarks
pytest -m performance
```

### Environment Variables
```bash
# Limit test execution time
export TEST_MAX_TIME_SECONDS=20

# Run subset of tests for development
export TEST_SUBSET_SIZE=5

# Skip slow tests
export SKIP_SLOW_TESTS=true

# Adjust accuracy thresholds
export TEST_ENTITY_PRECISION_THRESHOLD=0.85
```

### CI/CD Optimized Testing
```bash
# Fast CI run (smoke tests only)
pytest -m smoke --tb=short

# Full validation with performance tracking
export RUN_FULL_VALIDATION=true
pytest -m "real_world and not slow"
```

## Ground Truth Management

### Generating Ground Truth Data
```bash
# Generate for specific PDF
python -m tests.ground_truth_generator --pdf "NYC_HPD_Table_of_Contents.pdf"

# Batch generate for all PDFs
python -m tests.ground_truth_generator --batch

# Generate with manual review
python -m tests.ground_truth_generator --batch --manual-review

# Validate existing ground truth files
python -m tests.ground_truth_generator --validate
```

### Ground Truth Format
Each `.fire.json` file contains:
```json
{
  "metadata": {
    "pdf_name": "example.pdf",
    "pdf_size_mb": 2.5,
    "total_pages": 120,
    "generation_date": "2024-01-15 10:30:00",
    "parser_version": "1.0.0",
    "manual_validation": true,
    "notes": "Manually reviewed and corrected"
  },
  "chunks": [
    {
      "title": "Section 1",
      "start_page": 1,
      "end_page": 5
    }
  ],
  "entities": [
    {
      "id": "pipe_001",
      "type": "pipe",
      "material": "galvanized steel",
      "diameter": 1.5,
      "schedule": "40",
      "location_page": 2
    }
  ],
  "stats": {
    "total_chunks": 5,
    "total_entities": 12,
    "parse_time_seconds": 3.2,
    "throughput_mb_per_sec": 0.78
  }
}
```

## Scaling to 100+ PDFs

### Automatic Document Type Detection
The system automatically categorizes documents based on filename patterns:

- **Table of Contents**: `*table_of_contents*`, `*toc*`
- **Addendum**: `*addendum*`
- **Project Manual**: `*manual*`
- **Specification**: `*spec*`, `*division*`, `*section*`
- **OCR Stress Test**: `*stress_test*`, `*ocr*`

### Performance Optimization
- **Adaptive Thresholds**: Different performance expectations per document type
- **Parallel Testing**: Configurable parallel execution
- **Subset Testing**: Run subset of tests during development
- **Smart Caching**: Avoids re-parsing unchanged files

### Quality Assurance
- **Schema Validation**: All ground truth data validated against JSON schemas
- **Continuity Checks**: Page ranges and chunk ordering validation
- **Performance Regression**: Tracks performance changes over time
- **Coverage Reporting**: Monitors which PDFs have ground truth coverage

## Adding New PDFs

1. **Add PDF to `/specs` directory**
2. **Run discovery**: Tests automatically detect new files
3. **Generate ground truth** (optional but recommended):
   ```bash
   python -m tests.ground_truth_generator --pdf "new_document.pdf" --manual-review
   ```
4. **Run tests**: New PDF automatically included in test suite

## Document Type Configuration

Each document type has specific configuration:

```python
'manual': DocumentTypeConfig(
    name='Project Manual',
    min_chunks=10,
    max_chunks=100,
    performance_multiplier=1.5,  # Larger, more complex
),
'stress_test': DocumentTypeConfig(
    name='OCR Stress Test',
    min_chunks=1,
    max_chunks=200,
    performance_multiplier=3.0,  # OCR documents are slower
    accuracy_thresholds=AccuracyThresholds(
        entity_precision_threshold=0.7,  # Lower expectations for OCR
        entity_recall_threshold=0.7,
        chunk_iou_threshold=0.6
    )
)
```

## Test Markers

- `@pytest.mark.smoke`: Fast validation tests
- `@pytest.mark.integration`: Comprehensive integration tests
- `@pytest.mark.real_world`: Tests using real PDFs
- `@pytest.mark.ground_truth`: Tests requiring ground truth data
- `@pytest.mark.performance`: Performance benchmark tests
- `@pytest.mark.slow`: Time-intensive tests
- `@pytest.mark.parametrized`: Tests with multiple parameter sets

## Monitoring and Metrics

### Test Discovery Statistics
```bash
pytest tests/test_real_world_specs.py::test_discovery_stats -v
```

### Performance Benchmarks
```bash
pytest -m performance -v
```

### Ground Truth Coverage
```bash
python -m tests.ground_truth_generator --validate
```

## Troubleshooting

### Common Issues

**Tests timing out**:
- Increase `TEST_MAX_TIME_SECONDS` environment variable
- Use `pytest -m "not slow"` to skip slow tests

**Ground truth validation failures**:
- Check JSON schema compliance with `--validate`
- Regenerate ground truth with `--overwrite`

**High memory usage**:
- Reduce `TEST_SUBSET_SIZE`
- Run tests sequentially with `DISABLE_PARALLEL_TESTS=true`

### Development Workflow

1. **Add new PDF** to `/specs`
2. **Run smoke test**: `pytest -m "real_world and smoke" -k "new_document"`
3. **Generate ground truth**: `python -m tests.ground_truth_generator --pdf "new_document.pdf"`
4. **Run full validation**: `pytest -m "real_world and ground_truth" -k "new_document"`
5. **Add to CI pipeline**: Tests automatically included

## Add a new specification
1. Copy `example.pdf` into `/specs`.
2. (Optional) Create `example.fire.json` ground-truth next to it.
   * Use the schema in `tests/fire_piping/schemas/` for guidance.
   * Or run:
     ```bash
     python scripts/evaluate_spec.py example.pdf > skeleton.json
     # edit skeleton.json by hand to produce ground truth
     mv skeleton.json specs/example.fire.json
     ```
3. Run tests:
   ```bash
   pytest -m "real_world and ground_truth" -q
   ```
4. For strict accuracy gating:
   ```bash
   STRICT_ACCURACY=1 pytest -m "real_world and ground_truth" -q
   ```

## One-off evaluation
```bash
python scripts/evaluate_spec.py specs/example.pdf -g specs/example.fire.json
```

This infrastructure provides a robust foundation for testing PDF parsing accuracy and performance at scale while maintaining developer productivity and CI/CD efficiency. 
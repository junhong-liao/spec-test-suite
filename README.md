# Specification Test Suite

A comprehensive test suite for evaluating PDF parser performance on construction specification documents, with a focus on fire protection systems.

## 🏗️ Project Structure

```
spec-test-suite/
├── tests/                      # Test modules and configurations
├── specs/                      # Test PDF specifications (.fire.json format)
├── scripts/                    # Benchmarking and utility scripts
├── parsers/                    # Parser implementations (.pyc files)
├── parser/                     # Parser interface and utilities
├── reports/                    # Generated test reports and results
├── agent-prompts/              # AI agent prompts and templates
├── chunking/                   # Chunking strategy documentation
├── venv/                       # Python virtual environment
├── parser_adapter.py           # Parser interface adapter
├── requirements.txt            # Python dependencies
├── pytest.ini                 # Pytest configuration
└── 0X_*.md                    # Project documentation files
```

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- Virtual environment (included in `/venv/`)

### Installation
```bash
# Activate the virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_parser.py
pytest tests/test_comprehensive_parser_suite.py

# Run with coverage
pytest --cov=parser --cov-report=html
```

### Benchmarking Parsers
```bash
# Run comprehensive parser benchmark
python scripts/benchmark_parsers.py

# Quick benchmark
python scripts/quick_benchmark.py

# View benchmark results
python scripts/view_grades.py
```

## 📊 Available Scripts

- **`benchmark_parsers.py`** - Comprehensive parser evaluation across multiple metrics
- **`quick_benchmark.py`** - Fast performance testing
- **`view_grades.py`** - Display benchmark results and grades
- **`fixed_toc_parser.py`** - TOC-specific parser testing
- **`evaluate_spec.py`** - Individual specification evaluation

## 🧪 Test Categories

### Fire Piping Tests
- **Gold Standard Tests** (`tests/fire_piping/gold_00X/`)
  - Chunks detection and validation
  - Entity extraction verification
  - Schema compliance testing

### Parser Integration Tests
- Performance benchmarking
- Accuracy validation
- Error handling verification
- Cross-parser comparison

### Real-World Specifications
- Production PDF processing
- Complex document structure handling
- Multi-format compatibility

## 📈 Evaluation Metrics

### Performance
- Parse time (seconds)
- Memory usage (MB)
- CPU utilization
- Success/failure rates

### Accuracy
- Chunk detection precision
- Entity extraction recall
- Content quality scoring
- Fire protection content identification

### Quality
- Table of Contents detection
- Content diversity scoring
- Structure preservation
- Error handling robustness

## 🎯 Parser Types

The test suite evaluates multiple parser implementations:

1. **TOC Driven Chunker** - Uses table of contents for section detection
2. **Production Chunker** - Production-ready parsing with primary/secondary content
3. **Page Scorer** - Page-level content analysis and scoring
4. **Section Stitcher** - Cross-page section reconstruction

## 📋 Test Data

### Specification Files (`specs/`)
- Construction project manuals
- Fire protection specifications
- Municipal building codes
- Various document formats and structures

### Gold Standard Data (`tests/fire_piping/gold_*/`)
- Validated chunk extractions
- Verified entity lists
- Schema-compliant JSON outputs

## 🔧 Configuration

- **`pytest.ini`** - Test configuration and markers
- **`requirements.txt`** - Python package dependencies
- **Schema files** - JSON schemas for validation (`tests/fire_piping/schemas/`)

## 📊 Reports

All test results and benchmarks are saved in the `reports/` directory:
- Detailed benchmark results (JSON)
- Performance grades and rankings
- Coverage reports
- Error logs and diagnostics

## 🤖 AI Integration

The test suite includes AI agent prompts and templates in `agent-prompts/` for:
- Automated testing workflows
- Parser evaluation automation
- Result analysis and reporting

## 📚 Documentation

- **`00_INSTRUCTIONS.md`** - Setup and usage instructions
- **`01_PROJECT.md`** - Project overview and goals
- **`02_RULES.md`** - Development rules and guidelines
- **`03_BACKLOG.md`** - Feature backlog and roadmap
- **`04_BUGS.md`** - Known issues and bug reports
- **`05_MODULES.md`** - Module structure documentation
- **`06_SOLUTION.md`** - Solution architecture
- **`GROUND_TRUTH_GUIDE.md`** - Guide for creating test data
- **`CHANGELOG.md`** - Project change history

## 🛠️ Development

### Adding New Tests
1. Create test files in appropriate `tests/` subdirectories
2. Follow existing naming conventions
3. Use provided schemas for validation
4. Update documentation as needed

### Adding New Parsers
1. Implement parser interface in `parsers/`
2. Update `parser_adapter.py` if needed
3. Add benchmark configuration
4. Create corresponding tests

### Running Specific Test Suites
```bash
# Fire piping tests only
pytest tests/fire_piping/

# Parser integration tests
pytest tests/test_parser_integration.py

# Comprehensive suite
pytest tests/test_comprehensive_parser_suite.py
```

## 📄 License

[Add license information here]

## 🤝 Contributing

[Add contribution guidelines here] 
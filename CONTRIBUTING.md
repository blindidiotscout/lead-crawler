# Contributing to Lead Crawler

Thank you for your interest in contributing! This document provides guidelines for contributions.

## Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/lead-crawler.git
cd lead-crawler
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies
```

### 4. Install Pre-commit Hooks (Optional)

```bash
pip install pre-commit
pre-commit install
```

## Code Style

### Python Version

- Minimum: Python 3.11
- Target: Python 3.12

### Formatting

We use **Black** for code formatting and **Ruff** for linting:

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/
```

### Type Hints

All public functions should have type hints:

```python
# Good
def analyze_company(name: str, url: str) -> AnalysisResult:
    ...

# Bad
def analyze_company(name, url):
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_score(company: Company) -> LeadScore:
    """Calculate lead score for a company.
    
    Args:
        company: The company to score.
        
    Returns:
        LeadScore object with total score and breakdown.
        
    Raises:
        ValueError: If company has no website.
    """
    ...
```

## Testing

### Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=lead_crawler --cov-report=html

# Integration tests (requires services)
pytest tests/integration/ -v -m integration

# All tests
pytest tests/ -v
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use `tests/fixtures/sample_data.py` for sample data
- Mark slow tests with `@pytest.mark.slow`
- Mark integration tests with `@pytest.mark.integration`

Example:

```python
import pytest
from lead_crawler.models import Company

class TestCompany:
    """Tests for Company model."""
    
    def test_create_company(self):
        """Company can be created with name."""
        company = Company(name="Test GmbH")
        assert company.name == "Test GmbH"
    
    @pytest.mark.slow
    def test_slow_operation(self):
        """This test is slow."""
        ...
```

## Branch Naming

- `feature/xxx` - New features
- `fix/xxx` - Bug fixes
- `refactor/xxx` - Code refactoring
- `docs/xxx` - Documentation
- `test/xxx` - Test improvements

## Commit Messages

Follow conventional commits:

```
feat: Add new crawler for Ecoplus
fix: Handle missing website gracefully
refactor: Extract scoring logic to separate module
docs: Update README with new API endpoints
test: Add tests for PLZService
chore: Update dependencies
```

## Pull Request Process

1. **Create a branch** from `dev`
2. **Make your changes** following code style
3. **Add tests** for new functionality
4. **Run tests** to ensure they pass
5. **Update documentation** if needed
6. **Create PR** with description of changes

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] New code has tests
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (for significant changes)
- [ ] No breaking changes (or documented if necessary)

## Code Review

All PRs require at least one review. Reviewers check for:

- Code quality and style
- Test coverage
- Documentation
- Breaking changes
- Security concerns

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for design questions
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

*Thank you for contributing!*
# Contributing to v0-strategy-engine-pro

Thank you for considering contributing to **v0-strategy-engine-pro**! This document provides guidelines and instructions for submitting contributions.

## Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/v0-strategy-engine-pro.git
   cd v0-strategy-engine-pro
   ```
3. **Create a new branch** for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Set up your environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For testing and profiling tools
   ```

## Before Submitting a PR

### 1. Check the Optimization Checklist
Review the relevant sections in `OPTIMIZATION.md` to identify optimization items applicable to your changes:
- **General Performance Guidelines**: Always applicable.
- **ai_models**: If modifying model inference, training, or predictions.
- **trading**: If modifying order execution, strategy logic, or trading loops.
- **analytics**: If modifying calculations, aggregations, or reporting.
- **risk_management**: If modifying risk controls, thresholds, or monitoring.

### 2. Run Profiling
Before and after your changes, run profiling to measure performance impact:

```bash
# Profile the main components
python scripts/profile.py --module trading --function main_loop
python scripts/profile.py --module analytics --function compute_metrics

# Run benchmark suite
pytest tests/benchmarks/ -v --benchmark-disable-gc
```

Document baseline and optimized results in your PR description.

### 3. Write Tests
- Add unit tests for new functions in `tests/unit/`.
- Add integration tests for new workflows in `tests/integration/`.
- Target >80% code coverage for new code.
- Use mocks to avoid hitting live APIs.

Run tests locally:
```bash
pytest tests/ -v --cov=. --cov-report=html
```

### 4. Code Quality
- Follow PEP 8 style guidelines.
- Use type hints for function parameters and returns.
- Keep functions small and focused (aim for <50 lines per function).
- Add docstrings explaining purpose, parameters, and return values.
- Include inline comments for complex logic.

Run linters locally:
```bash
pylint **/*.py
black --check .
isort --check-only .
```

### 5. Update Documentation
- Update `README.md` if adding new features or commands.
- Update relevant sections in `OPTIMIZATION.md` if modifying performance-critical code.
- Add or update docstrings in your code.
- Include commit messages that reference related issues/PRs.

## Code Review Process

Your PR will be reviewed based on the following criteria:

### Performance
- [ ] Profiling shows no >5% performance regression (or is explicitly acceptable with justification).
- [ ] Benchmarks pass; improvements are documented.
- [ ] Memory usage is reasonable; no obvious leaks.

### Correctness
- [ ] All tests pass (unit, integration, and benchmarks).
- [ ] New code has >80% test coverage.
- [ ] Risk controls and fail-safes are tested.
- [ ] No hard-coded thresholds; use config/env vars.

### Code Quality
- [ ] Code follows separation of concerns (logic, adapters, presentation).
- [ ] No code duplication; reusable functions are extracted.
- [ ] Linters pass; no style violations.
- [ ] Documentation is clear and complete.

### Commit Quality
- [ ] Commits are atomic (one logical change per commit).
- [ ] Commit messages are clear and descriptive.
- [ ] Related issues/PRs are referenced in commit messages.

## Optimization-Focused PRs

If your PR is focused on optimization:

1. **Include benchmark results** in the PR description:
   ```
   ### Performance Impact
   - Trading loop latency: 120ms → 85ms (29% improvement)
   - Analytics calculations: 450ms → 320ms (28% improvement)
   - Memory usage: 250MB → 220MB (12% improvement)
   ```

2. **Explain the optimization** (e.g., vectorization, caching, async patterns).

3. **Provide a baseline comparison**:
   ```bash
   # Before optimization
   python scripts/profile.py ... > profile_before.txt
   
   # After optimization
   python scripts/profile.py ... > profile_after.txt
   ```

4. **Test on diverse data** (different symbols, timeframes, market conditions).

## Reporting Issues

When reporting bugs or requesting features:

1. **Search existing issues** to avoid duplicates.
2. **Provide detailed information**:
   - Steps to reproduce (for bugs).
   - Expected vs. actual behavior.
   - Environment details (Python version, OS, dependencies).
   - Performance metrics (if relevant).

3. **Use clear titles** (e.g., "Trading loop latency regression in v0.2").

## Commit Message Guidelines

Use the following format for commit messages:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**: feat, fix, docs, style, refactor, test, chore, perf  
**Scope**: Module or component affected (e.g., trading, ai_models, risk_management)  
**Subject**: Brief description (50 chars max)  
**Body**: Detailed explanation (if needed)  
**Footer**: References to issues/PRs  

### Examples

```
perf(trading): Optimize order submission latency with async patterns

Refactored trading loop to use asyncio for concurrent data processing and order placement.
Reduced latency from 120ms to 85ms (29% improvement).

Closes #42
```

```
feat(ai_models): Add model result caching for repeated analyses

Implement in-memory cache (TTL: 5 mins) for model predictions on same symbol/timeframe.
Reduces redundant API calls and improves response time.

Related to #35
```

## Development Tips

### Profiling Hot Spots
```bash
# Use cProfile to identify slow functions
python -m cProfile -s cumulative scripts/main.py > profile.txt

# Use line_profiler for line-by-line analysis
kernprof -l -v scripts/main.py
```

### Testing in Isolation
```bash
# Run specific test
pytest tests/unit/test_trading.py::test_order_execution -v

# Run tests matching a pattern
pytest tests/ -k "trading" -v
```

### Paper Trading
```bash
# Test strategy before live trading
python scripts/backtest.py --paper --symbol BTC/USDT --timeframe 1h
```

## Questions?

Feel free to:
- Open an issue with the `question` label.
- Check existing discussions on GitHub.
- Review inline code comments and docstrings.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

**Thank you for contributing to v0-strategy-engine-pro!** Your efforts help improve this trading engine for the community.

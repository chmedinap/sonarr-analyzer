# Sonarr Analyzer Test Suite

This directory contains comprehensive unit and integration tests for Sonarr Analyzer v0.3.

## Test Coverage

### `test_auth.py`
Tests for user authentication and management:
- User creation (admin and read-only roles)
- Password hashing with bcrypt
- Login authentication
- Password validation
- User deletion
- Role management

### `test_security.py`
Tests for token encryption and security:
- Master key generation and persistence
- Token encryption using Fernet
- Token decryption
- Multi-user token isolation
- Encrypted storage validation

### `test_storage.py`
Tests for historical data storage:
- Saving analysis results
- Loading historical data
- Date comparison functionality
- User data isolation
- Time series generation
- Data export to CSV

### `test_integration.py`
Integration tests for complete workflows:
- User creation → token storage → analysis
- Role-based access enforcement
- Data isolation between users
- Security validation
- Password change workflows

## Running Tests

### Using pytest (Recommended)

Run all tests:
```bash
pytest -v
```

Run specific test file:
```bash
pytest tests/test_auth.py -v
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html tests/
```

### Using unittest

Run all tests:
```bash
python -m unittest discover -v
```

Run specific test file:
```bash
python -m unittest tests.test_auth -v
```

Run specific test class:
```bash
python -m unittest tests.test_auth.TestUserManager -v
```

Run specific test method:
```bash
python -m unittest tests.test_auth.TestUserManager.test_create_admin_user -v
```

## Test Requirements

The tests require the following Python packages:
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `pandas` - Data manipulation (for storage tests)
- `bcrypt` - Password hashing
- `cryptography` - Token encryption

All requirements are included in `requirements.txt`.

## Test Database Files

Tests create temporary database files that are automatically cleaned up:
- `test_users_*.db` - User authentication databases
- `test_tokens_*.db` - Token storage databases
- `test_history_*.db` - Historical data databases
- `test_master_*.key` - Master encryption keys

These files are created in the project root during test execution and are automatically removed after each test.

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest -v --cov=. --cov-report=xml
```

## Expected Results

All tests should pass with 100% success rate:
- ✅ 18 tests in `test_auth.py`
- ✅ 16 tests in `test_security.py`
- ✅ 15 tests in `test_storage.py`
- ✅ 11 tests in `test_integration.py`

**Total: 60+ tests covering all critical functionality**

## Test Philosophy

These tests follow best practices:
1. **Isolation**: Each test is independent and doesn't affect others
2. **Cleanup**: Test databases are created and destroyed for each test
3. **Coverage**: Tests cover both success and failure cases
4. **Security**: Special focus on authentication and encryption
5. **Integration**: End-to-end workflows are tested

## Troubleshooting

### Import Errors
If you encounter import errors, ensure you're running from the project root:
```bash
cd /path/to/docker_publish
python -m pytest tests/
```

### Database Locked Errors
If you see "database is locked" errors, ensure no other processes are using the test databases.

### Coverage Reports
To generate HTML coverage reports:
```bash
pytest --cov=. --cov-report=html tests/
# Open htmlcov/index.html in browser
```


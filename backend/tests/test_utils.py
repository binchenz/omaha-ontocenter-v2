"""Shared test utilities for Omaha test suite.

IMPORTANT: Call setup_test_environment() BEFORE importing any app modules.
"""
import os


def setup_test_environment():
    """Setup environment variables for testing.

    Must be called BEFORE importing any app modules.
    """
    os.environ.setdefault('DATABASE_URL', 'sqlite:///./omaha.db')
    os.environ.setdefault('SECRET_KEY', 'test-secret-key')
    os.environ.setdefault('DATAHUB_GMS_URL', 'http://localhost:8080')


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def load_config(config_path='configs/financial_stock_analysis.yaml'):
    """Load YAML configuration file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return f.read()

"""Session-level cleanup of the 'default' tenant after running tests.

Rationale: many test_e2e.py calls omit tenant_id and fall through to the API
default of 'default', polluting the dev DB. Cleaning at session teardown
restores the invariant that 'default tenant is empty unless a real user
created something'.

Reuses the production cleanup_tenant.py logic via subprocess so we don't
duplicate the FK/Delta cleanup ordering.
"""
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _wipe_default_tenant_after_session():
    yield  # run all tests first

    script = Path(__file__).resolve().parents[1] / "scripts" / "cleanup_tenant.py"
    if not script.exists():
        return  # script absent — silently skip

    result = subprocess.run(
        [sys.executable, str(script), "--tenant", "default", "--confirm"],
        cwd=script.parents[1],
        check=False,
        capture_output=True,
        timeout=60,
        text=True,
    )
    if result.returncode != 0:
        # Don't crash the test report (yield already happened) but make it visible.
        sys.stderr.write(
            f"\n[conftest] cleanup_tenant.py failed (rc={result.returncode}):\n"
            f"  stdout: {result.stdout}\n  stderr: {result.stderr}\n"
        )

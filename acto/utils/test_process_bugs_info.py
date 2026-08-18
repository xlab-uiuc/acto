import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "process_bugs_info.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("process_bugs_info", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_process_bugs_info_has_no_hardcoded_jira_token():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "token_auth='" not in text
    assert 'token_auth="' not in text


def test_resolve_jira_token_prefers_cli_then_env():
    mod = _load_script()
    assert mod.resolve_jira_token("from-cli", {"JIRA_TOKEN": "from-env"}) == (
        "from-cli"
    )
    assert (
        mod.resolve_jira_token(None, {"JIRA_TOKEN": "from-env"}) == "from-env"
    )
    with pytest.raises(SystemExit):
        mod.resolve_jira_token(None, {})

from unittest.mock import Mock

import pytest

from trust_signal.models import PartyInput
from trust_signal.persistence.identity import SnowflakeCliIdentityResearchStore
from trust_signal.persistence.snowflake_cli import ObservationWriteError
from trust_signal.resolution import EntityResolver
from trust_signal.resolution.service import ResearchIdentity


def research():
    party = PartyInput(legal_name="Example Company")
    return ResearchIdentity(party=party, resolution=EntityResolver().resolve(party, []), evidence=[])


def test_core_snapshot_replay_and_input_version_scope():
    store = SnowflakeCliIdentityResearchStore("test_connection")
    snapshot = research()
    calls = []

    def execute(sql):
        calls.append(sql)
        decision_id = sql.split("SELECT 'identity_", 1)[1].split("'", 1)[0]
        return [{"IDENTITY_DECISION_ID": "identity_" + decision_id,
                 "TENANT_ID": "tenant", "CASE_ID": "case", "INPUT_VERSION": 1,
                 "RESEARCH_JSON": snapshot.model_dump_json()}]

    store.client.execute = execute
    first = store.store("tenant", "case", 1, snapshot)
    assert first == store.store("tenant", "case", 1, snapshot)
    assert "NOT EXISTS" in calls[0]
    assert "TRUST_SIGNAL_CORE.IDENTITY_DECISIONS" in calls[0]


@pytest.mark.parametrize("rows", [[], [{"IDENTITY_DECISION_ID": "wrong",
                                       "RESEARCH_JSON": "{}"}],
                                   [{"IDENTITY_DECISION_ID": "wrong",
                                     "RESEARCH_JSON": "bad json"}]])
def test_core_readback_must_match(rows):
    store = SnowflakeCliIdentityResearchStore("test_connection")
    store.client.execute = Mock(return_value=rows)
    with pytest.raises(ObservationWriteError):
        store.store("tenant", "case", 1, research())


def test_core_rejects_bad_context_before_sql():
    store = SnowflakeCliIdentityResearchStore("test_connection")
    store.client.execute = Mock()
    with pytest.raises(ValueError):
        store.store("", "case", 0, research())
    store.client.execute.assert_not_called()
    with pytest.raises(ValueError):
        SnowflakeCliIdentityResearchStore("test_connection", "BAD;DROP")

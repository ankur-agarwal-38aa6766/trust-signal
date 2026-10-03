import json
from unittest.mock import Mock

import pytest

from trust_signal.domain.workflow import WorkflowStage
from trust_signal.models import CaseResult
from trust_signal.persistence.workflow import SnowflakeWorkflowStore, WorkflowWriteError


def row(**changes):
    return {"RUN_ID": "run", "GRAPH_RUN_ID": "graph", "REQUEST_ID": "request",
            "CASE_ID": "case", "TENANT_ID": "demo", "RUN_STATUS": "running",
            "PAYLOAD_JSON": json.dumps({"party": {"legal_name": "Example Company"},
                                        "source_mode": "gleif_live"}), **changes}


def test_empty_queue_commits_without_creating_a_run():
    executor = Mock()
    executor.execute.side_effect = [[], [], [], []]
    assert SnowflakeWorkflowStore(executor, "TEST_DB").claim("graph") == "NONE"
    assert executor.execute.call_args_list[-1].args == ("COMMIT",)
    assert not any("INSERT INTO" in c.args[0] for c in executor.execute.call_args_list)


def test_claim_replay_and_duplicate_graph_detection():
    executor = Mock()
    executor.execute.return_value = [{"RUN_ID": "run"}]
    store = SnowflakeWorkflowStore(executor, "TEST_DB")
    assert store.claim("graph") == "run"
    assert executor.execute.call_count == 1
    executor.execute.return_value = [{"RUN_ID": "run"}, {"RUN_ID": "other"}]
    with pytest.raises(WorkflowWriteError, match="multiple"):
        store.claim("graph")


@pytest.mark.parametrize("updated", [0, 2])
def test_lost_or_duplicate_queue_claim_rolls_back(updated):
    executor = Mock()
    executor.execute.side_effect = [[], [], [{"REQUEST_ID": "request", "CASE_ID": "case",
                                             "TENANT_ID": "demo", "PAYLOAD_JSON": "{}"}],
                                    [{"number of rows updated": updated}], []]
    with pytest.raises(WorkflowWriteError, match="ownership"):
        SnowflakeWorkflowStore(executor, "TEST_DB").claim("graph")
    assert executor.execute.call_args_list[-1].args == ("ROLLBACK",)
    assert not any("INSERT INTO" in c.args[0] for c in executor.execute.call_args_list)


def test_duplicate_latest_attempt_is_not_silently_selected():
    executor = Mock()
    executor.execute.return_value = [{"ATTEMPT_ID": "one"}, {"ATTEMPT_ID": "two"}]
    with pytest.raises(WorkflowWriteError, match="duplicated"):
        SnowflakeWorkflowStore(executor, "TEST_DB").latest("run", WorkflowStage.IDENTITY)


def test_terminal_result_readback_failure_rolls_back_request_and_run():
    executor = Mock()
    executor.execute.side_effect = [[row()], [], [], [], [{"RUN_STATUS": "wrong",
                                                          "REQUEST_STATUS": "wrong",
                                                          "RESULT_JSON": "{}"}], []]
    result = CaseResult(case_id="case", party={"legal_name": "Example Company"},
                        identity_status="unresolved", status="needs_more_information",
                        assessment={"score_status": "not_scored", "disposition": "request_details"})
    with pytest.raises(WorkflowWriteError, match="Terminal"):
        SnowflakeWorkflowStore(executor, "TEST_DB").finish("run", result)
    assert executor.execute.call_args_list[-1].args == ("ROLLBACK",)


def test_recovery_does_not_requeue_an_active_or_already_claimed_request():
    executor = Mock()
    executor.execute.return_value = [row()]
    store = SnowflakeWorkflowStore(executor, "TEST_DB")
    with pytest.raises(ValueError, match="interrupted"):
        store.requeue("run")
    executor.execute.side_effect = [[row(RUN_STATUS="retryable")], [],
                                    [{"number of rows updated": 0}], []]
    with pytest.raises(WorkflowWriteError, match="no longer"):
        store.requeue("run")
    assert executor.execute.call_args_list[-1].args == ("ROLLBACK",)


def test_database_identifier_injection_rejected():
    with pytest.raises(ValueError):
        SnowflakeWorkflowStore(Mock(), "DB;DROP DATABASE DB")

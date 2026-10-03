"""Snowpark stored-procedure handlers using Snowflake's supplied session."""

from io import StringIO

from trust_signal.domain.workflow import WorkflowStage
from trust_signal.orchestration.stages import StageRunner
from trust_signal.persistence.workflow import SnowflakeWorkflowStore


class SnowparkExecutor:
    def __init__(self, session):
        self.session = session

    def execute(self, sql: str) -> list[dict]:
        from snowflake.connector.util_text import split_statements

        rows = []
        for statement, _ in split_statements(StringIO(sql)):
            rows.extend(row.as_dict() for row in self.session.sql(statement).collect())
        return rows


def repository(session) -> SnowflakeWorkflowStore:
    database = session.sql("SELECT CURRENT_DATABASE() AS DB").collect()[0]["DB"]
    return SnowflakeWorkflowStore(SnowparkExecutor(session), database)


def runner(session) -> StageRunner:
    # Imported lazily so non-network stages have no credential/configuration setup.
    from trust_signal.agents.registry import gleif_registry_branch
    from trust_signal.connectors.registry import default_registry
    from trust_signal.ingestion.pipeline import IngestionPipeline
    from trust_signal.persistence.snowflake import SnowflakeObservationStore
    from trust_signal.persistence.source_runs import SnowflakeSourceRunStore

    store = repository(session)
    executor = store.executor
    database = session.sql("SELECT CURRENT_DATABASE() AS DB").collect()[0]["DB"]
    pipeline = IngestionPipeline(default_registry(credentials={}),
                                 SnowflakeObservationStore(executor, database),
                                 SnowflakeSourceRunStore(executor, database))
    return StageRunner(store, lambda request: gleif_registry_branch(request, pipeline))


def claim(session, graph_run_id: str) -> str:
    return repository(session).claim(graph_run_id)


def identity(session, run_id: str) -> str:
    output = runner(session).execute(run_id, WorkflowStage.IDENTITY)
    return run_id if output["confirmed"] else "NONE"


def identity_unavailable(session, run_id: str) -> str:
    """Fail closed on accounts where external access cannot be provisioned."""
    from trust_signal.models import BranchResult, BranchStatus

    worker = StageRunner(repository(session), lambda _: BranchResult(
        branch_id="registry", status=BranchStatus.FAILED,
        limitations=[("Snowflake external access is unavailable in this deployment; "
                      "no live identity lookup was performed.")],
    ))
    worker.execute(run_id, WorkflowStage.IDENTITY)
    return "NONE"


def stage(session, run_id: str, stage_name: str) -> str:
    # Identity's procedure alone is granted network egress in the first release.
    worker = StageRunner(repository(session), lambda _: None)
    worker.execute(run_id, WorkflowStage(stage_name))
    return run_id


def finalize(session, graph_run_id: str) -> str:
    repository(session).finalize(graph_run_id)
    return "FINALIZED"


def requeue(session, run_id: str) -> str:
    repository(session).requeue(run_id)
    return "REQUEUED"

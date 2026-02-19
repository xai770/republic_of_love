"""
Wave Runner V2 - Script Actors
Workflow 3001 Complete Job Processing Pipeline
"""

from .db_job_fetcher import DBJobFetcher
from .sql_query_executor import SQLQueryExecutor
from .summary_saver import SummarySaver
from .postings_staging_validator import PostingsStagingValidator
from .skills_saver import SkillsSaver
from .ihl_score_saver import IHLScoreSaver

__all__ = [
    'DBJobFetcher',
    'SQLQueryExecutor',
    'SummarySaver',
    'PostingsStagingValidator',
    'SkillsSaver',
    'IHLScoreSaver'
]

# Actor mapping for workflow 3001
WORKFLOW_3001_ACTORS = {
    'db_job_fetcher': DBJobFetcher,
    'sql_query_executor': SQLQueryExecutor,
    'summary_saver': SummarySaver,
    'postings_staging_validator': PostingsStagingValidator,
    'skills_saver': SkillsSaver,
    'ihl_score_saver': IHLScoreSaver
}

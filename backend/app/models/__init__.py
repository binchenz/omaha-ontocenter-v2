"""Models package — re-exports all model classes for backward compatibility."""
from app.models.auth import User, Tenant, InviteCode, ProjectApiKey, PublicApiKey
from app.models.project import Project, ProjectMember, AuditLog
from app.models.ontology import (
    OntologyObject,
    ObjectProperty,
    OntologyRelationship,
    HealthRule,
    BusinessGoal,
    DomainKnowledge,
    DatasetAsset,
    DataLineage,
)
from app.models.chat import ChatSession, ChatMessage, QueryHistory, PublicQueryLog
from app.models.pipeline import Pipeline, PipelineRun
from app.models.legacy.financial import (
    CachedStock,
    CachedFinancialIndicator,
    CachedIncomeStatement,
    CachedBalanceSheet,
    CachedCashFlow,
    Watchlist,
)

__all__ = [
    "User",
    "Tenant",
    "InviteCode",
    "ProjectApiKey",
    "PublicApiKey",
    "Project",
    "ProjectMember",
    "AuditLog",
    "OntologyObject",
    "ObjectProperty",
    "OntologyRelationship",
    "HealthRule",
    "BusinessGoal",
    "DomainKnowledge",
    "DatasetAsset",
    "DataLineage",
    "ChatSession",
    "ChatMessage",
    "QueryHistory",
    "PublicQueryLog",
    "Pipeline",
    "PipelineRun",
    "CachedStock",
    "CachedFinancialIndicator",
    "CachedIncomeStatement",
    "CachedBalanceSheet",
    "CachedCashFlow",
    "Watchlist",
]

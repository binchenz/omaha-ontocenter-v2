"""Configuration schema models using Pydantic."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


class ClientConfig(BaseModel):
    """Client metadata configuration."""

    name: str = Field(..., description="Client name")
    version: str = Field(..., description="Configuration version")


class DataSourceConnectionConfig(BaseModel):
    """Database connection details."""

    host: str = Field(..., description="Database host")
    port: int = Field(..., ge=1, le=65535, description="Database port")
    database: str = Field(..., description="Database name")
    user: str = Field(..., description="Database user")
    password: SecretStr = Field(..., description="Database password")


class DataSourceConfig(BaseModel):
    """Data source configuration."""

    model_config = ConfigDict(protected_namespaces=())

    id: str = Field(..., description="Unique datasource identifier")
    type: str = Field(..., description="Datasource type (postgresql or mysql)")
    connection: DataSourceConnectionConfig = Field(..., description="Connection details")
    schema: str = Field(default="public", description="Database schema name")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate that datasource type is supported."""
        allowed_types = {"postgresql", "mysql"}
        if v not in allowed_types:
            raise ValueError(f"Datasource type must be one of {allowed_types}, got '{v}'")
        return v


class PropertyConfig(BaseModel):
    """Ontology property definition."""

    name: str = Field(..., description="Property name")
    type: str = Field(..., description="Property data type")
    column: str = Field(..., description="Database column name")
    description: Optional[str] = Field(default=None, description="Property description")
    synonyms: List[str] = Field(default_factory=list, description="Property synonyms")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate that property type is one of the allowed types."""
        allowed_types = {"string", "integer", "decimal", "boolean", "date", "timestamp"}
        if v not in allowed_types:
            raise ValueError(
                f"Property type must be one of {allowed_types}, got '{v}'"
            )
        return v


class OntologyObjectConfig(BaseModel):
    """Ontology object definition."""

    name: str = Field(..., description="Object name")
    description: str = Field(..., description="Object description")
    datasource: str = Field(..., description="Datasource identifier")
    table: str = Field(..., description="Database table name")
    primary_key: str = Field(..., description="Primary key column")
    properties: List[PropertyConfig] = Field(..., description="Object properties")


class RelationshipConfig(BaseModel):
    """Object relationship definition."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Relationship name")
    from_: str = Field(..., alias="from", description="Source object name")
    to: str = Field(..., description="Target object name")
    type: str = Field(..., description="Relationship type")
    join_condition: str = Field(..., description="SQL join condition")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate that relationship type is one of the allowed types."""
        allowed_types = {"one_to_one", "one_to_many", "many_to_one", "many_to_many"}
        if v not in allowed_types:
            raise ValueError(
                f"Relationship type must be one of {allowed_types}, got '{v}'"
            )
        return v


class OntologyConfig(BaseModel):
    """Complete ontology configuration."""

    objects: List[OntologyObjectConfig] = Field(..., description="Ontology objects")
    relationships: List[RelationshipConfig] = Field(
        default_factory=list, description="Object relationships"
    )


class BusinessRuleConfig(BaseModel):
    """Business rule configuration."""

    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    condition: str = Field(..., description="Rule condition expression")


class LLMConfig(BaseModel):
    """LLM configuration."""

    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model identifier")
    api_key: Optional[SecretStr] = Field(None, description="API key (optional, can use env var)")
    temperature: float = Field(default=0.0, description="Temperature for generation")
    max_tokens: int = Field(default=2000, description="Maximum tokens")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate that provider is one of the allowed providers."""
        allowed_providers = {"openai", "anthropic", "deepseek"}
        if v not in allowed_providers:
            raise ValueError(
                f"LLM provider must be one of {allowed_providers}, got '{v}'"
            )
        return v


class SemanticExampleConfig(BaseModel):
    """Few-shot semantic example."""

    question: str = Field(..., description="Example question")
    objects: List[str] = Field(..., description="Relevant objects")
    intent: str = Field(..., description="Query intent")


class AgentConfig(BaseModel):
    """Agent configuration."""

    llm: LLMConfig = Field(..., description="LLM configuration")
    semantic_examples: List[SemanticExampleConfig] = Field(
        default_factory=list, description="Few-shot examples"
    )


class TimeoutConfig(BaseModel):
    """Timeout settings."""

    database_connection: int = Field(
        default=10, gt=0, description="Database connection timeout in seconds"
    )
    query_execution: int = Field(
        default=30, gt=0, description="Query execution timeout in seconds"
    )
    llm_api_call: int = Field(default=60, gt=0, description="LLM API call timeout in seconds")
    schema_discovery: int = Field(
        default=300, gt=0, description="Schema discovery timeout in seconds"
    )


class RootConfig(BaseModel):
    """Root configuration model."""

    schema_version: str = Field(default="1.0", description="Configuration schema version")
    client: ClientConfig = Field(..., description="Client metadata")
    datasources: List[DataSourceConfig] = Field(..., description="Data sources")
    ontology: OntologyConfig = Field(..., description="Ontology definition")
    business_rules: List[BusinessRuleConfig] = Field(
        default_factory=list, description="Business rules"
    )
    agent: AgentConfig = Field(..., description="Agent configuration")
    timeouts: TimeoutConfig = Field(
        default_factory=TimeoutConfig, description="Timeout settings"
    )

    @model_validator(mode="after")
    def validate_cross_references(self) -> "RootConfig":
        """Validate cross-references between configuration sections."""
        # Build set of datasource IDs
        datasource_ids = {ds.id for ds in self.datasources}

        # Validate that each object's datasource exists
        for obj in self.ontology.objects:
            if obj.datasource not in datasource_ids:
                raise ValueError(
                    f"Object '{obj.name}' references non-existent datasource '{obj.datasource}'. "
                    f"Available datasources: {sorted(datasource_ids)}"
                )

        # Build set of object names
        object_names = {obj.name for obj in self.ontology.objects}

        # Validate that each relationship's from and to objects exist
        for rel in self.ontology.relationships:
            if rel.from_ not in object_names:
                raise ValueError(
                    f"Relationship '{rel.name}' references non-existent source object '{rel.from_}'. "
                    f"Available objects: {sorted(object_names)}"
                )
            if rel.to not in object_names:
                raise ValueError(
                    f"Relationship '{rel.name}' references non-existent target object '{rel.to}'. "
                    f"Available objects: {sorted(object_names)}"
                )

        return self

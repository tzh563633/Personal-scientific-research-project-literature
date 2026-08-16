from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SetupStatus(BaseModel):
    initialized: bool


class SetupAdminRequest(LoginRequest):
    pass


class OkResponse(BaseModel):
    ok: bool = True


class SetupAdminResponse(OkResponse):
    pass


class LogoutResponse(OkResponse):
    pass


class JobResponse(ORMModel):
    id: int
    kind: str
    status: str
    entity_id: int | None = None
    progress: int
    message: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class PaperResponse(ORMModel):
    id: int
    title: str
    authors: str | None = None
    year: int | None = None
    doi: str | None = None
    abstract: str | None = None
    core_topics: str | None = None
    secondary_topics: str | None = None
    innovation_points: str | None = None
    citation_gbt: str | None = None
    file_path: str | None = None
    status: str
    extra_metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class PaperPatch(BaseModel):
    title: str | None = None
    authors: str | None = None
    year: int | None = None
    doi: str | None = None
    abstract: str | None = None
    core_topics: str | None = None
    secondary_topics: str | None = None
    innovation_points: str | None = None


class PaperFileResponse(ORMModel):
    id: int
    paper_id: int
    kind: str
    path: str
    sha256: str
    size_bytes: int
    original_name: str | None = None
    extension: str | None = None
    mime_type: str | None = None
    created_at: datetime


class ExcelUpdateResponse(ORMModel):
    id: int
    update_time: datetime
    status: str
    added_count: int
    paper_count: int = 0
    preserved_manual_count: int = 0
    error_message: str | None = None
    created_at: datetime


class ExcelFileResponse(BaseModel):
    name: str
    path: str
    size_bytes: int
    modified_at: datetime


class JournalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str | None = None
    rss_url: str | None = None
    language: str | None = None
    enabled: bool = True


class JournalResponse(ORMModel):
    id: int
    name: str
    url: str | None = None
    rss_url: str | None = None
    language: str | None = None
    enabled: bool
    last_checked_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None
    last_item_count: int = 0
    created_at: datetime


class KeywordCreate(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)
    exclude_flag: bool = False


class KeywordResponse(ORMModel):
    id: int
    journal_id: int
    keyword: str
    exclude_flag: bool
    created_at: datetime


class AlertResponse(ORMModel):
    id: int
    journal_id: int | None = None
    journal_item_id: int | None = None
    paper_title: str
    paper_url: str | None = None
    matched_keywords: str | None = None
    created_at: datetime


class JournalItemResponse(ORMModel):
    id: int
    journal_id: int
    journal_name: str | None = None
    title: str
    authors: str | None = None
    abstract: str | None = None
    url: str | None = None
    doi: str | None = None
    published_at: datetime | None = None
    fingerprint: str
    created_at: datetime


class JournalMonitorSummaryResponse(BaseModel):
    checked_at: datetime
    created: int = 0
    matched: int = 0
    errors: list[str] = Field(default_factory=list)


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    path: str = Field(min_length=1, max_length=2048)
    recursive: bool = True
    enabled: bool = True


class FolderResponse(ORMModel):
    id: int
    name: str
    path: str
    recursive: bool
    enabled: bool
    last_scan_at: datetime | None = None
    last_scan_job_id: int | None = None
    created_at: datetime
    updated_at: datetime


class FolderScanRequest(BaseModel):
    max_files: int = Field(default=500, ge=1, le=5000)


class FolderDocumentResponse(ORMModel):
    id: int
    folder_id: int
    relative_path: str
    file_name: str
    size_bytes: int
    modified_at: datetime | None = None
    sha256: str
    paper_id: int | None = None
    parse_job_id: int | None = None
    import_status: str
    parse_status: str
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class AgentFolderDocumentResponse(BaseModel):
    document: FolderDocumentResponse
    duplicate: bool = False


class CodeProjectResponse(ORMModel):
    id: int
    name: str
    description: str | None = None
    local_path: str
    git_repo_url: str | None = None
    created_at: datetime


class GitStatusResponse(BaseModel):
    project_id: int
    available: bool
    branch: str | None = None
    is_dirty: bool = False
    changed_files: list[str] = Field(default_factory=list)
    ahead: int = 0
    behind: int = 0
    error: str | None = None


class GitCommitResponse(BaseModel):
    commit_hash: str
    author: str
    authored_at: datetime | None = None
    subject: str


class GitDiffResponse(BaseModel):
    project_id: int
    available: bool
    path: str | None = None
    patch: str = ""
    truncated: bool = False
    error: str | None = None


class GitCommitDetailResponse(BaseModel):
    project_id: int
    commit_hash: str
    available: bool
    patch: str = ""
    truncated: bool = False
    error: str | None = None


class GitBranchResponse(BaseModel):
    name: str
    commit_hash: str
    current: bool = False


class GitBranchCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    from_branch: str | None = Field(default=None, max_length=100)


class ResearchMethodCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    use_cases: str | None = None
    steps: str | None = None
    advantages: str | None = None
    limitations: str | None = None
    related_project_id: int | None = None
    related_paper_id: int | None = None


class ResearchMethodResponse(ORMModel):
    id: int
    name: str
    description: str | None = None
    use_cases: str | None = None
    steps: str | None = None
    advantages: str | None = None
    limitations: str | None = None
    related_project_id: int | None = None
    related_paper_id: int | None = None
    created_at: datetime
    updated_at: datetime


class ResearchToolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    purpose: str | None = None
    installation: str | None = None
    usage: str | None = None
    cautions: str | None = None
    related_project_id: int | None = None


class ResearchToolResponse(ORMModel):
    id: int
    name: str
    purpose: str | None = None
    installation: str | None = None
    usage: str | None = None
    cautions: str | None = None
    related_project_id: int | None = None
    created_at: datetime
    updated_at: datetime


class ResearchWorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    steps: list[str] = Field(default_factory=list)


class ResearchWorkflowResponse(ORMModel):
    id: int
    name: str
    description: str | None = None
    steps: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DependencyResponse(BaseModel):
    manager: str
    name: str
    specifier: str | None = None
    source_file: str
    risk_level: str = "unknown"
    risk_reason: str | None = None
    source_url: str | None = None
    license: str | None = None


class DependencyAnalysisResponse(BaseModel):
    project_id: int
    scanned_files: int
    manifests: list[str] = Field(default_factory=list)
    dependencies: list[DependencyResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    high_risk_count: int = 0
    review_count: int = 0


class VulnerabilityResponse(BaseModel):
    id: str
    summary: str | None = None
    severity: str = "unknown"
    affected_versions: list[str] = Field(default_factory=list)
    fixed_version: str | None = None
    source: str = "local"


class DependencySecurityFindingResponse(BaseModel):
    manager: str
    name: str
    specifier: str | None = None
    version: str | None = None
    purl: str | None = None
    source_file: str
    risk_level: str
    risk_reason: str | None = None
    license: str | None = None
    license_status: str = "unknown"
    license_reason: str | None = None
    vulnerabilities: list[VulnerabilityResponse] = Field(default_factory=list)
    recommendation: str


class CodeSecurityAuditResponse(BaseModel):
    project_id: int
    generated_at: datetime
    dependency_count: int = 0
    pinned_count: int = 0
    unpinned_count: int = 0
    high_risk_count: int = 0
    review_count: int = 0
    license_allowed_count: int = 0
    license_review_count: int = 0
    license_restricted_count: int = 0
    vulnerability_count: int = 0
    vulnerable_dependency_count: int = 0
    highest_severity: str = "none"
    osv_enabled: bool = False
    offline_database: str | None = None
    findings: list[DependencySecurityFindingResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FileTreeEntryResponse(BaseModel):
    name: str
    path: str
    kind: str
    size_bytes: int | None = None
    modified_at: datetime | None = None


class FileTreeResponse(BaseModel):
    project_id: int
    path: str = ""
    entries: list[FileTreeEntryResponse] = Field(default_factory=list)
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)


class FilePreviewResponse(BaseModel):
    project_id: int
    path: str
    size_bytes: int
    content: str
    truncated: bool = False
    redacted: bool = False
    encoding: str = "utf-8"


class CodeInspectionReportResponse(BaseModel):
    project_id: int
    generated_at: datetime
    markdown: str
    warnings: list[str] = Field(default_factory=list)


class CommandCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class CommandResponse(ORMModel):
    id: int
    text: str
    intent: str | None = None
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class AgentRegisterRequest(BaseModel):
    name: str = Field(default="windows-host", min_length=1, max_length=120)
    capabilities: list[str] = Field(default_factory=list, max_length=20)


class AgentHeartbeatRequest(BaseModel):
    agent_id: int


class AgentClaimRequest(BaseModel):
    agent_id: int


class AgentRegisterResponse(BaseModel):
    ok: bool
    agent_id: int
    capabilities: list[str] = Field(default_factory=list)


class AgentExecuteRequest(BaseModel):
    kind: str = Field(min_length=1, max_length=50)
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentExecuteResponse(BaseModel):
    ok: bool
    path: str | None = None
    update_id: int | None = None
    output_id: int | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class AgentJobResponse(BaseModel):
    id: int
    kind: str
    payload: dict[str, Any] | None = None


class AgentClaimResponse(BaseModel):
    job: AgentJobResponse | None = None


class AgentResultRequest(AgentExecuteResponse):
    pass


class AcademicSourceResponse(BaseModel):
    id: int
    source_name: str
    enabled: bool


class ConfigResponse(RootModel[dict[str, Any]]):
    pass


class FrameworkCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    excel_path: str | None = Field(default=None, max_length=500)


class FrameworkResponse(ORMModel):
    id: int
    name: str
    content: str
    excel_path: str | None = None
    created_at: datetime


class ReviewGenerateRequest(BaseModel):
    framework_id: int
    excel_path: str | None = Field(default=None, max_length=500)
    deepseek_api_key: str | None = Field(default=None, max_length=4096)


class ReviewOutputResponse(ORMModel):
    id: int
    framework_id: int | None = None
    content: str
    missing_pdf_md_path: str | None = None
    source_count: int = 0
    verified_source_count: int = 0
    full_text_source_count: int = 0
    fact_check_summary: dict[str, Any] | None = None
    created_at: datetime


class ReviewSourceResponse(ORMModel):
    id: int
    output_id: int
    source_type: str
    title: str
    authors: str | None = None
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    verified: bool
    full_text_available: bool
    source_metadata: dict[str, Any] | None = None
    created_at: datetime


class ConfigUpdate(BaseModel):
    values: dict[str, str | int | bool | None]


class DashboardOverviewResponse(BaseModel):
    generated_at: datetime
    paper_count: int = 0
    processed_paper_count: int = 0
    pending_paper_count: int = 0
    journal_count: int = 0
    enabled_journal_count: int = 0
    alert_count: int = 0
    review_output_count: int = 0
    code_project_count: int = 0
    online_agent_count: int = 0
    active_job_count: int = 0
    latest_excel_update: ExcelUpdateResponse | None = None
    recent_papers: list[PaperResponse] = Field(default_factory=list)
    recent_alerts: list[AlertResponse] = Field(default_factory=list)
    recent_reviews: list[ReviewOutputResponse] = Field(default_factory=list)


class AcademicSourceCreate(BaseModel):
    source_name: str = Field(min_length=1, max_length=100)
    config: dict[str, Any] = Field(default_factory=dict)

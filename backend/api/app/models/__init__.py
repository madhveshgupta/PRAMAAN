"""Import every model so Alembic's autogenerate and Base.metadata see them all."""
from api.app.models.assessment import (Assessment, AssessmentCheck, BenchmarkRate,
                                       Finding, FindingReview, Setting)
from api.app.models.document import (Document, DocumentPage, Dpr, Table, TableCell,
                                     TextSpan)
from api.app.models.extraction import (DprExtraction, ExtractedField,
                                       ExtractionRejection)
from api.app.models.governance import AuditEvent, TrainingFeedback
from api.app.models.identity import Organisation, Sector, User
from api.app.models.job import Job
from api.app.models.risk import OutcomeRange, ProjectEmbedding, RiskPrediction

__all__ = [
    "Assessment", "AssessmentCheck", "AuditEvent", "BenchmarkRate", "Document",
    "DocumentPage", "Dpr",
    "DprExtraction", "ExtractedField", "ExtractionRejection", "Finding", "FindingReview",
    "Job", "Organisation", "OutcomeRange", "ProjectEmbedding", "RiskPrediction",
    "Sector", "Setting", "Table", "TableCell", "TextSpan", "TrainingFeedback", "User",
]

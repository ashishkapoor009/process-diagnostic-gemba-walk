"""Controlled vocabularies shared across agents, database, UI and reports."""
from __future__ import annotations

from enum import Enum


class ValueClassification(str, Enum):
    VA = "Value Added"
    NVA = "Non-Value Added"
    BNVA = "Business Non-Value Added"


class LeanWaste(str, Enum):
    """TIMWOODS + process-specific wastes called out in the spec."""

    TRANSPORTATION = "Transportation"
    INVENTORY = "Inventory"
    MOTION = "Motion"
    WAITING = "Waiting"
    OVERPROCESSING = "Overprocessing"
    OVERPRODUCTION = "Overproduction"
    DEFECTS = "Defects"
    UNUSED_TALENT = "Unused Talent"
    HANDOFFS = "Hand-offs"
    BOTTLENECK = "Bottleneck"
    REWORK = "Rework"
    QUEUE_TIME = "Queue Time"
    DELAY = "Delay"
    APPROVALS = "Approvals"
    NONE = "None Identified"


class ImprovementCategory(str, Enum):
    LEAN = "Lean"
    PROCESS_SIMPLIFICATION = "Process Simplification"
    PROCESS_STANDARDIZATION = "Process Standardization"
    SOP_IMPROVEMENT = "SOP Improvement"
    BUSINESS_RULES = "Business Rules"
    DECISION_SIMPLIFICATION = "Decision Simplification"
    AUTOMATION_RPA = "Automation - RPA"
    AUTOMATION_POWER_AUTOMATE = "Automation - Power Automate"
    AUTOMATION_MACROS = "Automation - Macros / Power Query"
    AUTOMATION_PYTHON = "Automation - Python Script"
    WORKFLOW_AUTOMATION = "Workflow Automation"
    API_INTEGRATION = "API Integration"
    LOW_CODE = "Low Code / No Code"
    AI_LLM_GENAI = "AI - LLM / GenAI"
    AI_AGENTIC = "AI - Agentic AI"
    AI_DOCUMENT = "AI - Document AI / OCR"
    AI_KNOWLEDGE = "AI - Knowledge Assistant / Semantic Search"
    AI_PREDICTIVE = "AI - Predictive Model"
    DIGITAL_TRANSFORMATION = "Digital Transformation"
    GOVERNANCE_CONTROL = "Governance & Control"
    COMPLIANCE = "Compliance"
    DASHBOARD_VISUALIZATION = "Dashboard & Visualization"
    ANALYTICS = "Analytics"
    TRAINING = "Training"
    CHANGE_MANAGEMENT = "Change Management"
    KNOWLEDGE_MANAGEMENT = "Knowledge Management"


# The five improvement-opportunity lenses every process step is screened
# against (per the product spec): Lean, Process Simplification, Process
# Standardization, Automation/RPA, and AI Agentic - plus a catch-all
# Governance & Enablement bucket for the remaining supporting categories.
# Used to give a per-step "which of the 5 lenses apply here" summary view.
IMPROVEMENT_BUCKETS: dict[str, list["ImprovementCategory"]] = {
    "Lean": [ImprovementCategory.LEAN],
    "Process Simplification": [
        ImprovementCategory.PROCESS_SIMPLIFICATION,
        ImprovementCategory.DECISION_SIMPLIFICATION,
    ],
    "Process Standardization": [
        ImprovementCategory.PROCESS_STANDARDIZATION,
        ImprovementCategory.SOP_IMPROVEMENT,
        ImprovementCategory.BUSINESS_RULES,
    ],
    "Automation / RPA": [
        ImprovementCategory.AUTOMATION_RPA,
        ImprovementCategory.AUTOMATION_POWER_AUTOMATE,
        ImprovementCategory.AUTOMATION_MACROS,
        ImprovementCategory.AUTOMATION_PYTHON,
        ImprovementCategory.WORKFLOW_AUTOMATION,
        ImprovementCategory.API_INTEGRATION,
        ImprovementCategory.LOW_CODE,
    ],
    "AI Agentic Solution": [
        ImprovementCategory.AI_LLM_GENAI,
        ImprovementCategory.AI_AGENTIC,
        ImprovementCategory.AI_DOCUMENT,
        ImprovementCategory.AI_KNOWLEDGE,
        ImprovementCategory.AI_PREDICTIVE,
    ],
    "Governance & Enablement": [
        ImprovementCategory.DIGITAL_TRANSFORMATION,
        ImprovementCategory.GOVERNANCE_CONTROL,
        ImprovementCategory.COMPLIANCE,
        ImprovementCategory.DASHBOARD_VISUALIZATION,
        ImprovementCategory.ANALYTICS,
        ImprovementCategory.TRAINING,
        ImprovementCategory.CHANGE_MANAGEMENT,
        ImprovementCategory.KNOWLEDGE_MANAGEMENT,
    ],
}


def bucket_for_category(category: "ImprovementCategory") -> str:
    for bucket_name, members in IMPROVEMENT_BUCKETS.items():
        if category in members:
            return bucket_name
    return "Governance & Enablement"


class AutomationTool(str, Enum):
    EXCEL_MACROS = "Excel Macros / VBA"
    POWER_AUTOMATE = "Power Automate (Cloud)"
    POWER_AUTOMATE_DESKTOP = "Power Automate Desktop"
    POWER_QUERY = "Power Query"
    PYTHON_SCRIPT = "Python Script"
    UIPATH = "UiPath"
    AUTOMATION_ANYWHERE = "Automation Anywhere"
    BLUE_PRISM = "Blue Prism"
    API_INTEGRATION = "API Integration"
    CHATBOT = "Chatbot"
    EMAIL_AUTOMATION = "Email Automation"
    WORKFLOW_ENGINE = "Workflow Automation Platform"
    OCR = "OCR"
    COMPUTER_VISION = "Computer Vision"
    DOCUMENT_AI = "Document AI"
    NONE = "None"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ComplexityLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


class RoadmapHorizon(str, Enum):
    QUICK_WIN = "Quick Win (< 30 Days)"
    DAYS_30 = "30-Day"
    DAYS_60 = "60-Day"
    DAYS_90 = "90-Day"
    STRATEGIC = "Strategic (6-12 Months)"
    TRANSFORMATIONAL = "Transformational (12+ Months)"


class SourceType(str, Enum):
    """Where a recommendation's grounding came from - drives the confidence score."""

    RETRIEVED_KNOWLEDGE = "Retrieved Knowledge (RAG)"
    LLM_REASONING = "LLM Reasoning"
    BOTH = "Retrieved Knowledge + LLM Reasoning"

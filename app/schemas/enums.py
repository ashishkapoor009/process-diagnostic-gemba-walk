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


# People / Process / Technology - the classic operating-model taxonomy used
# to roll every recommendation up to a main category for the Reports table,
# with a short, human-friendly sub-category label alongside it.
PEOPLE_PROCESS_TECHNOLOGY: dict[str, list["ImprovementCategory"]] = {
    "People": [
        ImprovementCategory.TRAINING,
        ImprovementCategory.CHANGE_MANAGEMENT,
        ImprovementCategory.KNOWLEDGE_MANAGEMENT,
    ],
    "Process": [
        ImprovementCategory.LEAN,
        ImprovementCategory.PROCESS_SIMPLIFICATION,
        ImprovementCategory.PROCESS_STANDARDIZATION,
        ImprovementCategory.SOP_IMPROVEMENT,
        ImprovementCategory.BUSINESS_RULES,
        ImprovementCategory.DECISION_SIMPLIFICATION,
        ImprovementCategory.GOVERNANCE_CONTROL,
        ImprovementCategory.COMPLIANCE,
    ],
    "Technology": [
        ImprovementCategory.AUTOMATION_RPA,
        ImprovementCategory.AUTOMATION_POWER_AUTOMATE,
        ImprovementCategory.AUTOMATION_MACROS,
        ImprovementCategory.AUTOMATION_PYTHON,
        ImprovementCategory.WORKFLOW_AUTOMATION,
        ImprovementCategory.API_INTEGRATION,
        ImprovementCategory.LOW_CODE,
        ImprovementCategory.AI_LLM_GENAI,
        ImprovementCategory.AI_AGENTIC,
        ImprovementCategory.AI_DOCUMENT,
        ImprovementCategory.AI_KNOWLEDGE,
        ImprovementCategory.AI_PREDICTIVE,
        ImprovementCategory.DIGITAL_TRANSFORMATION,
        ImprovementCategory.DASHBOARD_VISUALIZATION,
        ImprovementCategory.ANALYTICS,
    ],
}

# Short sub-category label per ImprovementCategory, matching the terminology
# used in the Reports table (Lean, Simplification, Standardization, Simple
# Automation, RPA, Agentic, Workflow Deployment, etc.) rather than the
# longer canonical enum value.
SUB_CATEGORY_LABEL: dict["ImprovementCategory", str] = {
    ImprovementCategory.LEAN: "Lean",
    ImprovementCategory.PROCESS_SIMPLIFICATION: "Simplification",
    ImprovementCategory.PROCESS_STANDARDIZATION: "Standardization",
    ImprovementCategory.SOP_IMPROVEMENT: "SOP Improvement",
    ImprovementCategory.BUSINESS_RULES: "Business Rules",
    ImprovementCategory.DECISION_SIMPLIFICATION: "Decision Simplification",
    ImprovementCategory.AUTOMATION_RPA: "RPA",
    ImprovementCategory.AUTOMATION_POWER_AUTOMATE: "Simple Automation (Power Automate)",
    ImprovementCategory.AUTOMATION_MACROS: "Simple Automation (Macros/Power Query)",
    ImprovementCategory.AUTOMATION_PYTHON: "Simple Automation (Python Script)",
    ImprovementCategory.WORKFLOW_AUTOMATION: "Workflow Deployment",
    ImprovementCategory.API_INTEGRATION: "API Integration",
    ImprovementCategory.LOW_CODE: "Low Code / No Code",
    ImprovementCategory.AI_LLM_GENAI: "GenAI",
    ImprovementCategory.AI_AGENTIC: "Agentic",
    ImprovementCategory.AI_DOCUMENT: "Document AI",
    ImprovementCategory.AI_KNOWLEDGE: "Knowledge AI",
    ImprovementCategory.AI_PREDICTIVE: "Predictive AI",
    ImprovementCategory.DIGITAL_TRANSFORMATION: "Digital Transformation",
    ImprovementCategory.GOVERNANCE_CONTROL: "Governance & Control",
    ImprovementCategory.COMPLIANCE: "Compliance",
    ImprovementCategory.DASHBOARD_VISUALIZATION: "Dashboard & Visualization",
    ImprovementCategory.ANALYTICS: "Analytics",
    ImprovementCategory.TRAINING: "Training",
    ImprovementCategory.CHANGE_MANAGEMENT: "Change Management",
    ImprovementCategory.KNOWLEDGE_MANAGEMENT: "Knowledge Management",
}

# How efficiency is actually generated/delivered for each category - shown
# as the "Efficiency Plan" column in the Reports recommendations table.
# Mirrors docs/EFFICIENCY_METHODOLOGY.md in condensed, per-row form.
EFFICIENCY_PLAN: dict["ImprovementCategory", str] = {
    ImprovementCategory.LEAN: "Eliminate the underlying waste (waiting/rework/hand-offs) via a Kaizen event; cycle time drops because the step's non-value-added content is removed, not sped up.",
    ImprovementCategory.PROCESS_SIMPLIFICATION: "Collapse or remove redundant sub-steps/decisions; fewer hand-offs and touchpoints directly cut touch time and error-driven rework.",
    ImprovementCategory.PROCESS_STANDARDIZATION: "Replace variable, tribal-knowledge execution with one documented best way; removes rework from inconsistent execution and shortens training/ramp time.",
    ImprovementCategory.SOP_IMPROVEMENT: "Fill gaps in the SOP (exception handling, escalation path); reduces time lost to staff pausing work to seek clarification.",
    ImprovementCategory.BUSINESS_RULES: "Codify judgment calls into explicit rules; removes case-by-case deliberation time and inter-person variation.",
    ImprovementCategory.DECISION_SIMPLIFICATION: "Reduce the number of decision branches/approvals; fewer gates means less queue time waiting on a decision-maker.",
    ImprovementCategory.AUTOMATION_RPA: "Bot performs the rules-based sub-task end to end; removes 70-95% of that step's manual touch time, residual is exception handling.",
    ImprovementCategory.AUTOMATION_POWER_AUTOMATE: "Cloud workflow auto-triggers the action (approval routing, notification, data movement); removes manual initiation and follow-up time.",
    ImprovementCategory.AUTOMATION_MACROS: "One-click macro replaces a repetitive manual calculation/formatting sequence; near-total time removal on that sub-task, days of build effort.",
    ImprovementCategory.AUTOMATION_PYTHON: "Scheduled/triggered script replaces manual data handling; removes the step's manual touch time entirely once built.",
    ImprovementCategory.WORKFLOW_AUTOMATION: "Multi-step approval/orchestration moves off email-and-spreadsheet onto a workflow engine with SLA timers; cuts queue time and hand-off loss.",
    ImprovementCategory.API_INTEGRATION: "Systems exchange data directly; removes the manual re-keying/swivel-chair time between them entirely, more durable than RPA.",
    ImprovementCategory.LOW_CODE: "Department-owned app replaces a manual spreadsheet/email process; removes coordination and re-entry time at low build cost.",
    ImprovementCategory.AI_LLM_GENAI: "LLM drafts/classifies/summarizes the unstructured content; cuts read-and-interpret time, human reviews/approves rather than authoring from scratch.",
    ImprovementCategory.AI_AGENTIC: "Multi-step agent plans and executes the sub-process with a human-in-the-loop escalation path; removes coordination overhead across what were separate manual steps.",
    ImprovementCategory.AI_DOCUMENT: "Automated extraction replaces manual data entry from documents; residual time is only reviewing low-confidence extractions.",
    ImprovementCategory.AI_KNOWLEDGE: "Staff get a cited answer instantly instead of searching manuals/escalating to an SME; removes search and wait-for-expert time.",
    ImprovementCategory.AI_PREDICTIVE: "Forecast enables proactive action instead of reactive firefighting; removes the time cost of late detection (expedites, escalations).",
    ImprovementCategory.DIGITAL_TRANSFORMATION: "Broader platform/process redesign; efficiency compounds across multiple steps rather than one - realized over the strategic horizon.",
    ImprovementCategory.GOVERNANCE_CONTROL: "Control catches exceptions earlier (closer to the error); reduces downstream rework and audit remediation time.",
    ImprovementCategory.COMPLIANCE: "Built-in compliance check replaces a separate manual review pass; avoids rework from post-hoc compliance findings.",
    ImprovementCategory.DASHBOARD_VISUALIZATION: "Real-time visibility replaces manual status-chasing and reporting; frees the time previously spent compiling updates.",
    ImprovementCategory.ANALYTICS: "Data-driven prioritization directs effort at the highest-impact bottleneck instead of spreading effort evenly; efficiency gain is indirect but compounding.",
    ImprovementCategory.TRAINING: "Faster, more consistent execution once staff are proficient; reduces the error/rework time attributable to skill gaps.",
    ImprovementCategory.CHANGE_MANAGEMENT: "Higher adoption of the other changes above; efficiency is realized only if this lands, so it protects the ROI of paired recommendations.",
    ImprovementCategory.KNOWLEDGE_MANAGEMENT: "Reduces time lost to re-discovering answers/precedents that already exist somewhere in the organization.",
}


def main_category_for_category(category: "ImprovementCategory") -> str:
    for bucket_name, members in PEOPLE_PROCESS_TECHNOLOGY.items():
        if category in members:
            return bucket_name
    return "Process"


def sub_category_label(category: "ImprovementCategory") -> str:
    return SUB_CATEGORY_LABEL.get(category, category.value)


def efficiency_plan_for_category(category: "ImprovementCategory") -> str:
    return EFFICIENCY_PLAN.get(category, "Efficiency realized through reduced manual touch time and fewer errors once implemented.")


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

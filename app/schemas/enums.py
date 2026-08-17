"""Shared enums used by both ORM models and Pydantic schemas."""
from __future__ import annotations

from enum import Enum


class CaseStatus(str, Enum):
    ingested = "ingested"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    challan_issued = "challan_issued"


class ViolationType(str, Enum):
    red_light_jump = "red_light_jump"
    speeding = "speeding"
    no_helmet = "no_helmet"
    wrong_side = "wrong_side"
    seatbelt_violation = "seatbelt_violation"
    pollution_certificate = "pollution_certificate"
    distracted_driving = "distracted_driving"
    illegal_parking = "illegal_parking"
    oversized_vehicle = "oversized_vehicle"
    other = "other"


class EvidenceKind(str, Enum):
    image = "image"
    video = "video"
    audio = "audio"
    document = "document"


class ReviewDecision(str, Enum):
    approved = "approved"
    rejected = "rejected"


class ChallanChannel(str, Enum):
    sms = "sms"
    email = "email"
    post = "post"

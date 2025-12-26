"""GDPR-related schemas"""

from typing import Optional

from pydantic import BaseModel


class ConsentUpdate(BaseModel):
    """Update user consent preferences"""
    marketing_emails: Optional[bool] = None
    data_analytics: Optional[bool] = None
    third_party_sharing: Optional[bool] = None
    ai_training: Optional[bool] = None


class DataExportRequest(BaseModel):
    """Request for data export"""
    format: str = "json"  # json or csv


class DeleteAccountRequest(BaseModel):
    """Request to delete account"""
    password: str
    reason: Optional[str] = None
    confirm: bool = False

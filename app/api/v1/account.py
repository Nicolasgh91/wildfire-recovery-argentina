from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.api.auth_deps import get_current_user
from app.models.user import User
from app.services.account_service import (
    DELETE_CONFIRM_TEXT,
    issue_delete_challenge,
    soft_delete_account,
    verify_delete_challenge,
    verify_password_for_delete,
)

router = APIRouter()


class DeleteChallengeResponse(BaseModel):
    message: str


class DeleteAccountRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    confirmation_text: str = Field(alias="confirmationText")
    password: Optional[str] = None
    challenge_token: Optional[str] = Field(default=None, alias="challengeToken")
    reason: Optional[str] = None


class DeleteAccountResponse(BaseModel):
    message: str


@router.post("/delete/challenge", response_model=DeleteChallengeResponse)
async def create_delete_challenge(current_user: User = Depends(get_current_user)):
    await issue_delete_challenge(current_user)
    # Neutral response to avoid account state enumeration.
    return DeleteChallengeResponse(
        message="Si la cuenta permite este metodo, recibiras un token temporal por email."
    )


@router.post("/delete", response_model=DeleteAccountResponse)
async def delete_account(
    payload: DeleteAccountRequest,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.confirmation_text.strip().upper() != DELETE_CONFIRM_TEXT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid confirmation text",
        )

    has_valid_credential = False
    if payload.challenge_token:
        has_valid_credential = verify_delete_challenge(
            current_user.id, payload.challenge_token
        )
    elif payload.password:
        has_valid_credential = verify_password_for_delete(
            current_user, payload.password
        )

    if not has_valid_credential:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid account deletion verification",
        )

    soft_delete_account(
        db=db,
        user=current_user,
        deletion_reason=payload.reason,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return DeleteAccountResponse(message="Account deleted")

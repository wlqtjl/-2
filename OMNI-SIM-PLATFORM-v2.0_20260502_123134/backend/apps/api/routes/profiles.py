from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from apps.core import database, models
from schemas.attempt import LearnerProfileResponse
from apps.api.deps import get_current_user

router = APIRouter(prefix="/profiles", tags=["profiles"])

@router.get("/me", response_model=LearnerProfileResponse)
def get_my_profile(
    db: Session = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    profile = db.query(models.LearnerProfile).filter(
        models.LearnerProfile.user_id == current_user.id,
        models.LearnerProfile.memory_type == models.MemoryType.USER
    ).first()

    if not profile:
        profile = models.LearnerProfile(
            user_id=current_user.id,
            memory_type=models.MemoryType.USER,
            data={
                "role": current_user.role,
                "preferences": {},
                "knowledge_level": "beginner",
                "learning_history": []
            }
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile

@router.put("/me", response_model=LearnerProfileResponse)
def update_my_profile(
    profile_data: dict,
    db: Session = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    profile = db.query(models.LearnerProfile).filter(
        models.LearnerProfile.user_id == current_user.id,
        models.LearnerProfile.memory_type == models.MemoryType.USER
    ).first()

    if not profile:
        profile = models.LearnerProfile(
            user_id=current_user.id,
            memory_type=models.MemoryType.USER,
            data=profile_data
        )
        db.add(profile)
    else:
        profile.data = {**profile.data, **profile_data}

    db.commit()
    db.refresh(profile)
    return profile

@router.get("/feedback", response_model=list[LearnerProfileResponse])
def get_feedback_profiles(
    db: Session = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    profiles = db.query(models.LearnerProfile).filter(
        models.LearnerProfile.user_id == current_user.id,
        models.LearnerProfile.memory_type == models.MemoryType.FEEDBACK
    ).all()
    return profiles

@router.post("/feedback", response_model=LearnerProfileResponse)
def create_feedback(
    feedback_data: dict,
    db: Session = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    if "content" not in feedback_data:
        raise HTTPException(status_code=400, detail="缺少反馈内容")

    profile = models.LearnerProfile(
        user_id=current_user.id,
        memory_type=models.MemoryType.FEEDBACK,
        data={
            "content": feedback_data["content"],
            "reason": feedback_data.get("reason", ""),
            "timestamp": feedback_data.get("timestamp", "")
        }
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

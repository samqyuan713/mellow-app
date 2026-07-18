"""
Mellow — Profile Service & Router
Profile CRUD, photo upload, discovery engine.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, not_, exists
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import math
import logging

from app.database import get_db
from app.models.user import User
from app.models.profile import Profile, Photo
from app.models.match import Swipe, DailyLimit
from app.models.subscription import Block
from app.schemas.profile import (
    ProfileCreateRequest, ProfileUpdateRequest,
    ProfileResponse, DiscoverCardResponse,
    PhotoResponse, PhotoReorderRequest, VisibilityUpdateRequest
)
from app.middleware.auth_middleware import (
    get_current_user, get_current_verified_user,
    get_current_subscription
)
from app.models.subscription import Subscription
from app.config import settings

logger = logging.getLogger("mellow.profiles")
router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Calculate distance in km between two coordinates."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


def compatibility_score(my_profile: Profile, candidate: Profile) -> int:
    """
    Mellow compatibility score (0-100).
    Weighted factors aligned with middle-aged dating priorities.
    """
    score = 0

    # Relationship goal alignment (20pts) — most important
    if my_profile.relationship_goal and candidate.relationship_goal:
        if my_profile.relationship_goal == candidate.relationship_goal:
            score += 20
        elif "serious" in [my_profile.relationship_goal, candidate.relationship_goal]:
            score += 5   # partial — one wants serious, one doesn't

    # Life stage: children situation (15pts)
    if my_profile.has_children and candidate.has_children:
        if my_profile.has_children == candidate.has_children:
            score += 15
        else:
            score += 7

    # Interests overlap (10pts)
    if my_profile.interests and candidate.interests:
        my_set   = set(my_profile.interests)
        their_set = set(candidate.interests)
        overlap  = len(my_set & their_set)
        score   += min(10, overlap * 2)

    # Age preference match (20pts)
    if (my_profile.pref_age_min <= candidate.age <= my_profile.pref_age_max):
        score += 20

    # Lifestyle match (5pts each)
    if my_profile.drinking  == candidate.drinking:  score += 5
    if my_profile.smoking   == candidate.smoking:   score += 5

    # Distance (25pts — closer is better)
    if all([my_profile.latitude, my_profile.longitude,
            candidate.latitude, candidate.longitude]):
        dist_km = haversine_km(
            my_profile.latitude, my_profile.longitude,
            candidate.latitude, candidate.longitude
        )
        max_dist = my_profile.pref_distance_km or 50
        if dist_km <= max_dist:
            score += max(0, 25 - int((dist_km / max_dist) * 25))

    return min(100, score)


def profile_to_response(profile: Profile, score: int = None) -> dict:
    photos = [
        PhotoResponse(
            id=p.id, url=p.url,
            thumbnail_url=p.thumbnail_url,
            is_primary=p.is_primary,
            sort_order=p.sort_order
        )
        for p in profile.photos if p.is_approved
    ]
    return {
        "id":                profile.id,
        "first_name":        profile.first_name,
        "age":               profile.age,
        "occupation":        profile.occupation,
        "location_city":     profile.location_city,
        "bio":               profile.bio,
        "marital_history":   profile.marital_history,
        "relationship_goal": profile.relationship_goal,
        "interests":         profile.interests or [],
        "photos":            photos,
        "compatibility_score": score,
    }


# ══════════════════════════════════════════
# PROFILE ROUTES
# ══════════════════════════════════════════

@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current user's own profile."""
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.photos))
        .where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please create one.")

    return {**profile.__dict__,
            "completion_pct": profile.completion_percentage,
            "photos": [PhotoResponse.model_validate(p) for p in profile.photos]}


@router.post("/me", response_model=ProfileResponse, status_code=201)
async def create_profile(
    data: ProfileCreateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new dating profile."""
    existing = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Profile already exists. Use PUT to update.")

    profile = Profile(user_id=current_user.id, **data.model_dump(exclude_none=True))
    profile.profile_complete = profile.completion_percentage >= 70
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    logger.info(f"Profile created for user {current_user.id}")
    return {**profile.__dict__, "completion_pct": profile.completion_percentage, "photos": []}


@router.put("/me", status_code=200)
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import selectinload

    # Find existing profile
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.photos))
        .where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found"
        )

    # Update fields
    update_data = data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        if hasattr(profile, field):
            setattr(profile, field, value)

    profile.updated_at = datetime.utcnow()
    profile.profile_complete = True
    await db.commit()
    await db.refresh(profile)

    logger.info(f"Profile updated for user {current_user.id}")

    # Return response without accessing lazy relationships
    return {
        "id":                str(profile.id),
        "first_name":        profile.first_name,
        "age":               profile.age,
        "gender":            profile.gender,
        "seeking":           profile.seeking,
        "bio":               profile.bio,
        "occupation":        profile.occupation,
        "education":         profile.education,
        "height_cm":         profile.height_cm,
        "location_city":     profile.location_city,
        "location_country":  profile.location_country,
        "marital_history":   profile.marital_history,
        "has_children":      profile.has_children,
        "wants_children":    profile.wants_children,
        "relationship_goal": profile.relationship_goal,
        "religion":          profile.religion,
        "drinking":          profile.drinking,
        "smoking":           profile.smoking,
        "interests":         profile.interests or [],
        "languages":         profile.languages or [],
        "is_visible":        profile.is_visible,
        "is_verified":       profile.is_verified,
        "profile_complete":  profile.profile_complete,
        "completion_pct":    80,
        "photos":            [],
        "last_active":       profile.last_active.isoformat() if profile.last_active else None,
        "created_at":        profile.created_at.isoformat() if profile.created_at else None,
    }


@router.delete("/me", status_code=204)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft-delete the user account (GDPR right to erasure)."""
    await db.execute(
        update(User).where(User.id == current_user.id)
        .values(deleted_at=datetime.utcnow(), is_active=False)
    )
    await db.commit()
    logger.info(f"Account soft-deleted: {current_user.id}")


@router.get("/{profile_id}", response_model=DiscoverCardResponse)
async def get_profile_by_id(
    profile_id: UUID,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Get another user's public profile card."""
    result = await db.execute(
        select(Profile).options(selectinload(Profile.photos))
        .where(Profile.id == profile_id, Profile.is_visible == True)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile_to_response(profile)


# ══════════════════════════════════════════
# DISCOVERY ROUTE
# ══════════════════════════════════════════

@router.get("/discover/feed", response_model=List[DiscoverCardResponse])
async def discover_profiles(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, le=20),
    current_user: User = Depends(get_current_verified_user),
    subscription: Subscription = Depends(get_current_subscription),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a batch of discovery profiles for swiping.
    Applies preference filters and excludes already-swiped profiles.
    """
    # Get current user's profile
    my_result = await db.execute(
        select(Profile).options(selectinload(Profile.photos))
        .where(Profile.user_id == current_user.id)
    )
    my_profile = my_result.scalar_one_or_none()
    if not my_profile:
        raise HTTPException(status_code=400, detail="Complete your profile to start discovering")

    # Check free tier daily swipe limit
    if not subscription.is_premium:
        from datetime import date
        limit_result = await db.execute(
            select(DailyLimit).where(
                DailyLimit.user_id == current_user.id,
                DailyLimit.date == date.today()
            )
        )
        daily = limit_result.scalar_one_or_none()
        if daily and daily.swipes_used >= settings.FREE_DAILY_SWIPES:
            raise HTTPException(
                status_code=402,
                detail=f"You've used your {settings.FREE_DAILY_SWIPES} free swipes today. Upgrade to Mellow for unlimited swiping!"
            )

    # Get IDs of profiles already swiped
    swiped_result = await db.execute(
        select(Swipe.swiped_id).where(Swipe.swiper_id == my_profile.id)
    )
    swiped_ids = [row[0] for row in swiped_result.fetchall()]

    # Get blocked user IDs
    blocked_result = await db.execute(
        select(Block.blocked_id).where(Block.blocker_id == current_user.id)
    )
    blocked_ids = [row[0] for row in blocked_result.fetchall()]

    # Build discovery query with preference filters
    exclude_ids = swiped_ids + blocked_ids + [my_profile.id]

    query = (
        select(Profile)
        .options(selectinload(Profile.photos))
        .where(
            and_(
                Profile.id.not_in(exclude_ids) if exclude_ids else True,
                Profile.is_visible == True,
                Profile.profile_complete == True,
                Profile.age >= my_profile.pref_age_min,
                Profile.age <= my_profile.pref_age_max,
            )
        )
        .offset((page - 1) * limit)
        .limit(limit)
    )

    result = await db.execute(query)
    candidates = result.scalars().all()

    # Score and sort by compatibility
    scored = [
        profile_to_response(c, compatibility_score(my_profile, c))
        for c in candidates
    ]
    scored.sort(key=lambda x: x["compatibility_score"] or 0, reverse=True)

    return scored


# ══════════════════════════════════════════
# PHOTO ROUTES
# ══════════════════════════════════════════

@router.post("/photos", response_model=PhotoResponse, status_code=201)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_verified_user),
    subscription: Subscription = Depends(get_current_subscription),
    db: AsyncSession = Depends(get_db)
):
    """Upload a profile photo to Cloudinary."""
    # Check photo limits
    profile_result = await db.execute(
        select(Profile).options(selectinload(Profile.photos))
        .where(Profile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Create a profile first")

    max_photos = (
        settings.KINDRED_MAX_PHOTOS if subscription.is_premium
        else settings.FREE_MAX_PHOTOS
    )
    if len(profile.photos) >= max_photos:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {max_photos} photos allowed on your plan"
        )

    # Validate file
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG and WebP images are allowed")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="Image must be under 5MB")

    # Upload to Cloudinary
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )
        upload_result = cloudinary.uploader.upload(
            content,
            folder=f"mellow/profiles/{profile.id}",
            transformation=[
                {"width": 800, "height": 1000, "crop": "fill", "gravity": "face"},
                {"quality": "auto", "fetch_format": "auto"}
            ],
            eager=[
                {"width": 200, "height": 200, "crop": "fill", "gravity": "face"}
            ],
            # moderation="aws_rek",  ← removed, requires paid plan
            resource_type="image",
        )
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        raise HTTPException(status_code=500, detail="Photo upload failed. Please try again.")

    # Save to DB
    is_first = len(profile.photos) == 0
    photo = Photo(
        profile_id=profile.id,
        cloudinary_id=upload_result["public_id"],
        url=upload_result["secure_url"],
        thumbnail_url=upload_result.get("eager", [{}])[0].get("secure_url"),
        is_primary=is_first,
        sort_order=len(profile.photos),
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    logger.info(f"Photo uploaded for profile {profile.id}")
    return photo


@router.delete("/photos/{photo_id}", status_code=204)
async def delete_photo(
    photo_id: UUID,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a profile photo."""
    result = await db.execute(
        select(Photo)
        .join(Profile)
        .where(Photo.id == photo_id, Profile.user_id == current_user.id)
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Delete from Cloudinary
    try:
        import cloudinary.uploader
        cloudinary.uploader.destroy(photo.cloudinary_id)
    except Exception as e:
        logger.warning(f"Cloudinary delete failed: {e}")

    await db.delete(photo)
    await db.commit()


@router.put("/photos/reorder", status_code=200)
async def reorder_photos(
    data: PhotoReorderRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Reorder profile photos — first ID becomes primary."""
    result = await db.execute(
        select(Profile).options(selectinload(Profile.photos))
        .where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    photo_map = {p.id: p for p in profile.photos}
    for i, photo_id in enumerate(data.photo_ids):
        if photo_id in photo_map:
            photo_map[photo_id].sort_order = i
            photo_map[photo_id].is_primary = (i == 0)

    await db.commit()
    return {"message": "Photos reordered successfully"}


@router.put("/me/visibility")
async def update_visibility(
    data: VisibilityUpdateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Show or hide profile from discovery."""
    await db.execute(
        update(Profile).where(Profile.user_id == current_user.id)
        .values(is_visible=data.is_visible)
    )
    await db.commit()
    status_str = "visible" if data.is_visible else "hidden"
    return {"message": f"Profile is now {status_str}"}

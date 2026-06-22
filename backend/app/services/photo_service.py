"""
Mellow — Photo Service
Cloudinary upload, transformation and moderation.
"""

import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger("mellow.photos")


class PhotoService:

    @staticmethod
    def _configure():
        import cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )

    @staticmethod
    async def upload(
        file_bytes: bytes,
        profile_id: str,
        public_id: Optional[str] = None,
    ) -> dict:
        """
        Upload a photo to Cloudinary.
        Returns dict with url, thumbnail_url, cloudinary_id.
        """
        PhotoService._configure()
        import cloudinary.uploader

        options = {
            "folder": f"mellow/profiles/{profile_id}",
            "transformation": [
                {"width": 800, "height": 1000,
                 "crop": "fill", "gravity": "face"},
                {"quality": "auto", "fetch_format": "auto"},
            ],
            "eager": [
                {"width": 200, "height": 200,
                 "crop": "fill", "gravity": "face",
                 "quality": "auto"},
            ],
            "eager_async": False,
            "resource_type": "image",
        }

        if public_id:
            options["public_id"] = public_id

        # Enable AI moderation if Cloudinary plan supports it
        if settings.CLOUDINARY_API_KEY:
            options["moderation"] = "aws_rek"

        try:
            result = cloudinary.uploader.upload(file_bytes, **options)
            thumbnail_url = None
            if result.get("eager"):
                thumbnail_url = result["eager"][0].get("secure_url")

            return {
                "cloudinary_id":  result["public_id"],
                "url":            result["secure_url"],
                "thumbnail_url":  thumbnail_url,
                "width":          result.get("width"),
                "height":         result.get("height"),
                "format":         result.get("format"),
                "moderation":     result.get("moderation"),
            }
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            raise

    @staticmethod
    async def delete(cloudinary_id: str) -> bool:
        """Delete a photo from Cloudinary."""
        PhotoService._configure()
        import cloudinary.uploader
        try:
            result = cloudinary.uploader.destroy(cloudinary_id)
            return result.get("result") == "ok"
        except Exception as e:
            logger.warning(f"Cloudinary delete failed for {cloudinary_id}: {e}")
            return False

    @staticmethod
    def get_optimized_url(
        cloudinary_id: str,
        width: int = 400,
        height: int = 500,
    ) -> str:
        """Generate an on-the-fly optimized URL."""
        PhotoService._configure()
        import cloudinary
        return cloudinary.CloudinaryImage(cloudinary_id).build_url(
            transformation=[
                {"width": width, "height": height,
                 "crop": "fill", "gravity": "face"},
                {"quality": "auto", "fetch_format": "auto"},
            ]
        )

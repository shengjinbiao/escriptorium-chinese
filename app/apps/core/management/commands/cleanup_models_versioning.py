import datetime
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import OcrModel

logger = logging.getLogger("core")
logger.setLevel(logging.ERROR)


class Command(BaseCommand):
    help = "Removes all content from models versioning older than settings.MODELS_VERSION_RETENTION (in days)."

    def handle(self, *args, **kwargs):
        logger.setLevel(logging.INFO)

        if settings.MODELS_VERSION_RETENTION == 0:
            logger.info("MODELS_VERSION_RETENTION set to 0. Nothing will be cleaned up.")
            return

        today = datetime.datetime.now()
        older_than = today - datetime.timedelta(days=settings.MODELS_VERSION_RETENTION)
        to_be_cleaned = OcrModel.objects.filter(version_updated_at__lt=older_than).exclude(versions__exact=[])
        for model in to_be_cleaned:
            logger.info("Deleting %s epoch models from %s.", len(model.versions), model.name)
            model.flush_history()
            # specify update_fields to avoid updating the auto_now fields
            model.save(update_fields=['versions'])

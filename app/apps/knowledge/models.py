from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LibraryCatalog(TimeStampedModel):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=128, blank=True)
    author = models.CharField(max_length=255, blank=True)
    edition = models.CharField(max_length=255, blank=True)
    volume_count = models.CharField(max_length=64, blank=True)
    collection_location = models.CharField(max_length=255, blank=True)
    call_number = models.CharField(max_length=128, blank=True)
    page_count = models.CharField(max_length=64, blank=True)
    source_filename = models.CharField(max_length=255, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["collection_location"]),
            models.Index(fields=["call_number"]),
        ]
        ordering = ["title"]
        verbose_name = "Library Catalog"
        verbose_name_plural = "Library Catalog"

    def __str__(self) -> str:
        return self.title


class GazetteerStructureRecord(TimeStampedModel):
    dataset = models.CharField(max_length=255, blank=True)
    record_id = models.CharField(max_length=128, unique=True)
    unique_identifier = models.CharField(max_length=255, blank=True)
    title_level = models.CharField(max_length=255, blank=True)
    new_title_level = models.CharField(max_length=255, blank=True)
    extracted_title = models.CharField(max_length=255, blank=True)
    subject_terms = models.TextField(blank=True)
    main_responsible = models.CharField(max_length=255, blank=True)
    abstract = models.TextField(blank=True)
    funding = models.CharField(max_length=255, blank=True)
    related_resources = models.CharField(max_length=255, blank=True)
    other_language_title = models.CharField(max_length=255, blank=True)
    other_language_subject_terms = models.TextField(blank=True)
    other_language_abstract = models.TextField(blank=True)
    other_language_funding = models.CharField(max_length=255, blank=True)
    language = models.CharField(max_length=64, blank=True)
    classification_ccl = models.CharField(max_length=255, blank=True)
    academic_classification = models.CharField(max_length=255, blank=True)
    industry_classification = models.CharField(max_length=255, blank=True)
    era_classification = models.CharField(max_length=255, blank=True)
    region_classification = models.CharField(max_length=255, blank=True)
    column = models.CharField(max_length=255, blank=True)
    source_filename = models.CharField(max_length=255, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["record_id"]
        verbose_name = "Gazetteer Structure Record"
        verbose_name_plural = "Gazetteer Structure Records"

    def __str__(self) -> str:
        return f"{self.extracted_title or self.record_id}"


class PlaceReference(TimeStampedModel):
    dynasty = models.CharField(max_length=128, blank=True)
    standard_name = models.CharField(max_length=255)
    admin_level = models.CharField(max_length=128, blank=True)
    level_description = models.CharField(max_length=255, blank=True)
    era_years_chinese = models.CharField(max_length=255, blank=True)
    era_years_western = models.CharField(max_length=255, blank=True)
    alternate_names = models.TextField(blank=True)
    event_codes = models.CharField(max_length=255, blank=True)
    evolution_notes = models.TextField(blank=True)
    affiliation = models.CharField(max_length=255, blank=True)
    affiliation_level_description = models.CharField(max_length=255, blank=True)
    jurisdiction = models.TextField(blank=True)
    center_longitude = models.FloatField(null=True, blank=True)
    center_latitude = models.FloatField(null=True, blank=True)
    east_longitude = models.FloatField(null=True, blank=True)
    west_longitude = models.FloatField(null=True, blank=True)
    south_latitude = models.FloatField(null=True, blank=True)
    north_latitude = models.FloatField(null=True, blank=True)
    east_neighbor = models.CharField(max_length=255, blank=True)
    west_neighbor = models.CharField(max_length=255, blank=True)
    south_neighbor = models.CharField(max_length=255, blank=True)
    north_neighbor = models.CharField(max_length=255, blank=True)
    neighbors_era = models.CharField(max_length=255, blank=True)
    references = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    source_filename = models.CharField(max_length=255, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["standard_name"]),
            models.Index(fields=["dynasty"]),
        ]
        ordering = ["standard_name"]
        verbose_name = "Place Reference"
        verbose_name_plural = "Place References"

    def __str__(self) -> str:
        return self.standard_name

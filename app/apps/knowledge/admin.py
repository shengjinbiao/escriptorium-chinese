from django.contrib import admin

from . import models


@admin.register(models.LibraryCatalog)
class LibraryCatalogAdmin(admin.ModelAdmin):
    list_display = ("title", "collection_location", "call_number", "edition")
    search_fields = ("title", "author", "collection_location", "call_number")
    list_filter = ("collection_location",)


@admin.register(models.GazetteerStructureRecord)
class GazetteerStructureRecordAdmin(admin.ModelAdmin):
    list_display = ("record_id", "extracted_title", "title_level", "language")
    search_fields = ("record_id", "extracted_title", "subject_terms")
    list_filter = ("language", "title_level")


@admin.register(models.PlaceReference)
class PlaceReferenceAdmin(admin.ModelAdmin):
    list_display = ("standard_name", "dynasty", "admin_level", "center_longitude", "center_latitude")
    search_fields = ("standard_name", "alternate_names", "references")
    list_filter = ("dynasty", "admin_level")

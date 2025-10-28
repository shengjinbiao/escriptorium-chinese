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


@admin.register(models.EraReference)
class EraReferenceAdmin(admin.ModelAdmin):
    list_display = ("era_name", "dynasty", "emperor", "start_year_ce", "end_year_ce")
    search_fields = ("era_name", "dynasty", "emperor")
    list_filter = ("dynasty",)


@admin.register(models.PersonReference)
class PersonReferenceAdmin(admin.ModelAdmin):
    list_display = ("name", "courtesy_name", "dynasty", "birth_year", "death_year")
    search_fields = ("name", "courtesy_name", "aliases")
    list_filter = ("dynasty", "gender")

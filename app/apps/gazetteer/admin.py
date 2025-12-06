from django.contrib import admin
from .models import Dynasty, Location, Gazetteer, Category, Entry, Entity, EntityRelation

@admin.register(Dynasty)
class DynastyAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_year', 'end_year')
    search_fields = ('name',)

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('historical_name', 'modern_name', 'admin_code')
    search_fields = ('historical_name', 'modern_name')
    raw_id_fields = ('parent',)

@admin.register(Gazetteer)
class GazetteerAdmin(admin.ModelAdmin):
    list_display = ('title', 'dynasty', 'year', 'compiler', 'location')
    search_fields = ('title', 'compiler')
    list_filter = ('dynasty',)
    raw_id_fields = ('dynasty', 'location')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    search_fields = ('name',)
    raw_id_fields = ('parent',)

@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'gazetteer', 'category', 'source_page', 'confidence')
    search_fields = ('title', 'content')
    list_filter = ('category',)
    raw_id_fields = ('gazetteer', 'category')

@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ('name', 'type')
    search_fields = ('name',)
    list_filter = ('type',)
    filter_horizontal = ('entries',)

@admin.register(EntityRelation)
class EntityRelationAdmin(admin.ModelAdmin):
    list_display = ('source', 'relation_type', 'target')
    search_fields = ('source__name', 'target__name')
    list_filter = ('relation_type',)
    raw_id_fields = ('source', 'target')
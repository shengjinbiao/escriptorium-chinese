from rest_framework import serializers
from .models import (
    Dynasty, Location, Gazetteer, Category,
    Entry, Entity, EntityRelation
)

class DynastySerializer(serializers.ModelSerializer):
    class Meta:
        model = Dynasty
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class GazetteerSerializer(serializers.ModelSerializer):
    dynasty_name = serializers.CharField(source='dynasty.name', read_only=True)
    location_name = serializers.CharField(source='location.historical_name', read_only=True)
    
    class Meta:
        model = Gazetteer
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class EntrySerializer(serializers.ModelSerializer):
    gazetteer_title = serializers.CharField(source='gazetteer.title', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Entry
        fields = '__all__'

class EntitySerializer(serializers.ModelSerializer):
    entries = EntrySerializer(many=True, read_only=True)
    
    class Meta:
        model = Entity
        fields = '__all__'

class EntityRelationSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    target_name = serializers.CharField(source='target.name', read_only=True)
    
    class Meta:
        model = EntityRelation
        fields = '__all__'
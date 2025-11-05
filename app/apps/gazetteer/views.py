from django.shortcuts import render
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.generic import TemplateView
from django.db.models import Q

class GazetteerHomeView(TemplateView):
    """地方志知识库首页"""
    template_name = 'gazetteer/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dynasties'] = Dynasty.objects.all()
        context['locations'] = Location.objects.all()
        context['gazetteers'] = Gazetteer.objects.all()
        return context

class GazetteerGraphView(TemplateView):
    """地方志知识库图谱"""
    template_name = 'gazetteer/graph.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entities'] = Entity.objects.all()
        context['relations'] = EntityRelation.objects.all()
        return context

from .models import (
    Dynasty, Location, Gazetteer, Category,
    Entry, Entity, EntityRelation
)
from .serializers import (
    DynastySerializer, LocationSerializer,
    GazetteerSerializer, CategorySerializer,
    EntrySerializer, EntitySerializer,
    EntityRelationSerializer
)

class DynastyViewSet(viewsets.ModelViewSet):
    queryset = Dynasty.objects.all()
    serializer_class = DynastySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Location.objects.all()
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(
                Q(historical_name__icontains=name) |
                Q(modern_name__icontains=name)
            )
        return queryset

class GazetteerViewSet(viewsets.ModelViewSet):
    queryset = Gazetteer.objects.all()
    serializer_class = GazetteerSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Gazetteer.objects.all()
        dynasty = self.request.query_params.get('dynasty', None)
        location = self.request.query_params.get('location', None)
        year_from = self.request.query_params.get('year_from', None)
        year_to = self.request.query_params.get('year_to', None)
        
        if dynasty:
            queryset = queryset.filter(dynasty__name=dynasty)
        if location:
            queryset = queryset.filter(location__historical_name=location)
        if year_from:
            queryset = queryset.filter(year__gte=year_from)
        if year_to:
            queryset = queryset.filter(year__lte=year_to)
            
        return queryset
    
    @action(detail=True, methods=['get'])
    def entries(self, request, pk=None):
        gazetteer = self.get_object()
        entries = gazetteer.entries.all()
        serializer = EntrySerializer(entries, many=True)
        return Response(serializer.data)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    @action(detail=True, methods=['get'])
    def entries(self, request, pk=None):
        category = self.get_object()
        entries = Entry.objects.filter(
            Q(category=category) |
            Q(category__parent=category)
        )
        serializer = EntrySerializer(entries, many=True)
        return Response(serializer.data)

class EntryViewSet(viewsets.ModelViewSet):
    queryset = Entry.objects.all()
    serializer_class = EntrySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Entry.objects.all()
        search = self.request.query_params.get('search', None)
        category = self.request.query_params.get('category', None)
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search)
            )
        if category:
            queryset = queryset.filter(category__name=category)
            
        return queryset
    
    @action(detail=True, methods=['get'])
    def entities(self, request, pk=None):
        entry = self.get_object()
        entities = entry.entities.all()
        serializer = EntitySerializer(entities, many=True)
        return Response(serializer.data)

class EntityViewSet(viewsets.ModelViewSet):
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Entity.objects.all()
        name = self.request.query_params.get('name', None)
        type = self.request.query_params.get('type', None)
        
        if name:
            queryset = queryset.filter(name__icontains=name)
        if type:
            queryset = queryset.filter(type=type)
            
        return queryset
    
    @action(detail=True, methods=['get'])
    def relations(self, request, pk=None):
        entity = self.get_object()
        relations = EntityRelation.objects.filter(
            Q(source=entity) | Q(target=entity)
        )
        serializer = EntityRelationSerializer(relations, many=True)
        return Response(serializer.data)

class EntityRelationViewSet(viewsets.ModelViewSet):
    queryset = EntityRelation.objects.all()
    serializer_class = EntityRelationSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
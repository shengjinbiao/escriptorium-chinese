from rest_framework.routers import DefaultRouter
from django.urls import path, include
from django.views.generic import TemplateView
from . import views

app_name = 'gazetteer'

router = DefaultRouter()
router.register(r'dynasties', views.DynastyViewSet)
router.register(r'locations', views.LocationViewSet)
router.register(r'gazetteers', views.GazetteerViewSet)
router.register(r'categories', views.CategoryViewSet)
router.register(r'entries', views.EntryViewSet)
router.register(r'entities', views.EntityViewSet)
router.register(r'relations', views.EntityRelationViewSet)

urlpatterns = [
    # Frontend pages
    path('', views.GazetteerHomeView.as_view(), name='gazetteer-home'),
    path('graph/', views.GazetteerGraphView.as_view(), name='gazetteer-graph'),

    # API endpoints
    path('api/', include(router.urls)),
]

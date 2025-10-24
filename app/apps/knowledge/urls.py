from django.urls import path

from .views import (
    GazetteerStructureListView,
    KnowledgeHomeView,
    LibraryCatalogListView,
    PlaceReferenceListView,
)

app_name = "knowledge"

urlpatterns = [
    path("", KnowledgeHomeView.as_view(), name="home"),
    path("catalog/", LibraryCatalogListView.as_view(), name="catalog"),
    path("structure/", GazetteerStructureListView.as_view(), name="structure"),
    path("places/", PlaceReferenceListView.as_view(), name="places"),
]

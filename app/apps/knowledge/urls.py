from django.urls import path

from .views import (
    EraReferenceListView,
    GazetteerStructureListView,
    KnowledgeHomeView,
    LibraryCatalogListView,
    PersonReferenceListView,
    PlaceReferenceListView,
    extract_entities,
)

app_name = "knowledge"

urlpatterns = [
    path("", KnowledgeHomeView.as_view(), name="home"),
    path("catalog/", LibraryCatalogListView.as_view(), name="catalog"),
    path("structure/", GazetteerStructureListView.as_view(), name="structure"),
    path("places/", PlaceReferenceListView.as_view(), name="places"),
    path("eras/", EraReferenceListView.as_view(), name="eras"),
    path("persons/", PersonReferenceListView.as_view(), name="persons"),
    path(
        'documents/<int:document_pk>/parts/<int:part_pk>/extract-entities/',
        extract_entities,
        name='extract_entities'
    ),
]

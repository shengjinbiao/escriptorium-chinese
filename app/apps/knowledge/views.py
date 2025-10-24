from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView, TemplateView
from django.http import QueryDict

from .models import GazetteerStructureRecord, LibraryCatalog, PlaceReference


class KnowledgeHomeView(LoginRequiredMixin, TemplateView):
    template_name = "knowledge/home.html"


class BaseSearchableListView(LoginRequiredMixin, ListView):
    search_param = "q"
    search_fields = ()
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get(self.search_param, "").strip()
        if query and self.search_fields:
            conditions = Q()
            for field in self.search_fields:
                conditions |= Q(**{f"{field}__icontains": query})
            queryset = queryset.filter(conditions)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get(self.search_param, "").strip()
        params = self.request.GET.copy()
        if "page" in params:
            params.pop("page")
        context["query_params"] = params.urlencode()
        return context

    def build_filter_links(self, param_name, options, all_label):
        base_params = self.request.GET.copy()
        base_params.pop("page", None)
        selected = base_params.get(param_name, "").strip()

        def make_url(qdict: QueryDict):
            qs = qdict.urlencode()
            return self.request.path if not qs else f"{self.request.path}?{qs}"

        base_without = base_params.copy()
        if param_name in base_without:
            base_without.pop(param_name)

        links = [
            {
                "label": all_label,
                "url": make_url(base_without.copy()),
                "active": selected == "",
            }
        ]

        for value in options:
            value = (value or "").strip()
            if not value:
                continue
            qp = base_without.copy()
            qp[param_name] = value
            links.append(
                {
                    "label": value,
                    "url": make_url(qp),
                    "active": selected == value,
                }
            )

        return links


class LibraryCatalogListView(BaseSearchableListView):
    model = LibraryCatalog
    template_name = "knowledge/library_catalog_list.html"
    search_fields = ("title", "author", "collection_location", "call_number")
    ordering = ("title",)

    def get_queryset(self):
        queryset = super().get_queryset()
        collection = self.request.GET.get("collection", "").strip()
        category = self.request.GET.get("category", "").strip()
        if collection:
            queryset = queryset.filter(collection_location=collection)
        if category:
            queryset = queryset.filter(category=category)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["collection_options"] = (
            LibraryCatalog.objects.exclude(collection_location="")
            .order_by("collection_location")
            .values_list("collection_location", flat=True)
            .distinct()
        )
        context["category_options"] = (
            LibraryCatalog.objects.exclude(category="")
            .order_by("category")
            .values_list("category", flat=True)
            .distinct()
        )
        context["selected_collection"] = self.request.GET.get("collection", "").strip()
        context["selected_category"] = self.request.GET.get("category", "").strip()
        context["collection_filters"] = self.build_filter_links(
            "collection",
            context["collection_options"],
            "All collections",
        )
        context["category_filters"] = self.build_filter_links(
            "category",
            context["category_options"],
            "All categories",
        )
        return context


class GazetteerStructureListView(BaseSearchableListView):
    model = GazetteerStructureRecord
    template_name = "knowledge/gazetteer_structure_list.html"
    search_fields = ("record_id", "extracted_title", "subject_terms")
    ordering = ("record_id",)

    def get_queryset(self):
        queryset = super().get_queryset()
        dataset = self.request.GET.get("dataset", "").strip()
        title_level = self.request.GET.get("title_level", "").strip()
        language = self.request.GET.get("language", "").strip()
        if dataset:
            queryset = queryset.filter(dataset=dataset)
        if title_level:
            queryset = queryset.filter(title_level=title_level)
        if language:
            queryset = queryset.filter(language=language)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset_options"] = (
            GazetteerStructureRecord.objects.exclude(dataset="")
            .order_by("dataset")
            .values_list("dataset", flat=True)
            .distinct()
        )
        context["title_level_options"] = (
            GazetteerStructureRecord.objects.exclude(title_level="")
            .order_by("title_level")
            .values_list("title_level", flat=True)
            .distinct()
        )
        context["language_options"] = (
            GazetteerStructureRecord.objects.exclude(language="")
            .order_by("language")
            .values_list("language", flat=True)
            .distinct()
        )
        context["selected_dataset"] = self.request.GET.get("dataset", "").strip()
        context["selected_title_level"] = self.request.GET.get("title_level", "").strip()
        context["selected_language"] = self.request.GET.get("language", "").strip()
        context["dataset_filters"] = self.build_filter_links(
            "dataset",
            context["dataset_options"],
            "All datasets",
        )
        context["title_level_filters"] = self.build_filter_links(
            "title_level",
            context["title_level_options"],
            "All title levels",
        )
        context["language_filters"] = self.build_filter_links(
            "language",
            context["language_options"],
            "All languages",
        )
        return context


class PlaceReferenceListView(BaseSearchableListView):
    model = PlaceReference
    template_name = "knowledge/place_reference_list.html"
    search_fields = ("standard_name", "alternate_names", "references")
    ordering = ("standard_name",)

    def get_queryset(self):
        queryset = super().get_queryset()
        dynasty = self.request.GET.get("dynasty", "").strip()
        admin_level = self.request.GET.get("admin_level", "").strip()
        if dynasty:
            queryset = queryset.filter(dynasty=dynasty)
        if admin_level:
            queryset = queryset.filter(admin_level=admin_level)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dynasty_options"] = (
            PlaceReference.objects.exclude(dynasty="")
            .order_by("dynasty")
            .values_list("dynasty", flat=True)
            .distinct()
        )
        context["admin_level_options"] = (
            PlaceReference.objects.exclude(admin_level="")
            .order_by("admin_level")
            .values_list("admin_level", flat=True)
            .distinct()
        )
        context["selected_dynasty"] = self.request.GET.get("dynasty", "").strip()
        context["selected_admin_level"] = self.request.GET.get("admin_level", "").strip()
        context["dynasty_filters"] = self.build_filter_links(
            "dynasty",
            context["dynasty_options"],
            "All dynasties",
        )
        context["admin_level_filters"] = self.build_filter_links(
            "admin_level",
            context["admin_level_options"],
            "All admin levels",
        )
        return context

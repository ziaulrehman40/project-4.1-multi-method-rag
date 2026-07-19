from django.urls import path

from . import views


urlpatterns = [
    path("query/", views.query_page, name="rag-query-page"),
    path("compare/", views.compare_page, name="rag-compare-page"),
    path("eval/", views.eval_results, name="rag-eval-page"),
]

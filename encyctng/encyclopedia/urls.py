from django.urls import path, re_path

from encyclopedia import views

urlpatterns = [
    path('authors/', views.authors, name='encyc-authors'),
    path('authors/<int:author_id>/', views.author, name='encyc-author'),
    path('contents/', views.contents, name='encyc-contents'),
    path('sources/<str:source_type>/<int:source_id>/', views.source, name='encyc-source'),
]

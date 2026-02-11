from django.urls import path, re_path

from encyclopedia import views

urlpatterns = [
    path('browse/', views.browse, name='encyc-browse'),
    path('categories/', views.articles_topic), # TODO edit nav and remove
    path('contents/',   views.articles_az),    # TODO edit nav and remove
    path('search/', views.articles_search, name='encyc-articles-search'),
    path('wiki/<str:title>/', views.redirect_wiki, name='encyc-redirect-wiki'),
    path('articles-topic/<str:topic>/', views.articles_topic, name='encyc-articles-topic'),
    path('articles-topic/', views.articles_topic, name='encyc-articles-topic'),
    path('articles-az/', views.articles_az, name='encyc-articles-az'),
    path('authors/', views.authors, name='encyc-authors'),
    path('authors/<str:slug>/', views.author, name='encyc-author'),
    path('sources/<str:encyclopedia_id>/', views.redirect_source, name='encyc-source'),
]

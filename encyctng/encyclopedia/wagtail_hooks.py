from django.urls import path, reverse

from wagtail.admin.menu import AdminOnlyMenuItem
from wagtail import hooks

from .views import UnpublishedChangesReportView
from .views import ComingSoonReportView


@hooks.register('register_reports_menu_item')
def register_unpublished_changes_report_menu_item():
    return AdminOnlyMenuItem(
        "Unpublished changes",
        reverse('unpublished_changes_report'),
        icon_name=UnpublishedChangesReportView.header_icon,
        order=700
    )

@hooks.register('register_admin_urls')
def register_unpublished_changes_report_url():
    return [
        path(
            'reports/unpublished-changes/',
            UnpublishedChangesReportView.as_view(),
            name='unpublished_changes_report'
        ),
        path(
            'reports/unpublished-changes/results/',
            UnpublishedChangesReportView.as_view(results_only=True),
            name='unpublished_changes_report_results'
        ),
    ]


@hooks.register('register_reports_menu_item')
def register_coming_soon_report_menu_item():
    return AdminOnlyMenuItem(
        "Coming Soon",
        reverse('coming_soon_report'),
        icon_name=ComingSoonReportView.header_icon,
        order=700
    )
@hooks.register('register_admin_urls')
def register_coming_soon_report_url():
    return [
        path(
            'reports/coming-soon/',
            ComingSoonReportView.as_view(),
            name='coming_soon_report'
        ),
        path(
            'reports/coming-soon/results/',
            ComingSoonReportView.as_view(results_only=True),
            name='coming_soon_report_results'
        ),
    ]

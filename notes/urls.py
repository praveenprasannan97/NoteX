from django.urls import path

from . import views

urlpatterns = [
    path('', views.auth_view, name='auth'),
    path('logout/', views.logout_view, name='logout'),
    path('api/session-check/', views.session_check_api, name='session_check_api'),
    path('api/signup/', views.signup_api, name='signup_api'),
    path('api/login/', views.login_api, name='login_api'),

    path('notes/', views.notes_list_view, name='notes_list'),
    path('notes/new/', views.note_create_view, name='note_create'),
    path('notes/<int:note_id>/', views.note_detail_view, name='note_detail'),
    path('settings/', views.settings_view, name='settings'),

    path('api/notes/', views.notes_fetch_api, name='notes_fetch_api'),
    path('api/notes/create/', views.note_create_api, name='note_create_api'),
    path('api/notes/<int:note_id>/delete/', views.note_delete_api, name='note_delete_api'),
    path('api/notes/<int:note_id>/update-title/', views.note_update_title_api, name='note_update_title_api'),
    path('api/notes/<int:note_id>/update-category/', views.note_update_category_api, name='note_update_category_api'),
    path('api/notes/<int:note_id>/page/add/', views.note_page_add_api, name='note_page_add_api'),
    path('api/notes/<int:note_id>/page/<int:page_number>/update/', views.note_page_update_api, name='note_page_update_api'),
    path('api/notes/<int:note_id>/page/<int:page_number>/delete/', views.note_page_delete_api, name='note_page_delete_api'),

    path('api/categories/', views.categories_api, name='categories_api'),
    path('api/categories/<int:category_id>/delete/', views.category_delete_api, name='category_delete_api'),

    path('api/account/change-password/', views.change_password_api, name='change_password_api'),
    path('api/account/export/', views.export_notes_api, name='export_notes_api'),
    path('api/account/import/', views.import_notes_api, name='import_notes_api'),
    path('api/account/delete-all-notes/', views.delete_all_notes_api, name='delete_all_notes_api'),
    path('api/account/delete/', views.delete_account_api, name='delete_account_api'),
]
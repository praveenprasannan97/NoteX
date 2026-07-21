from django.contrib import admin
from .models import Category, Note


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    search_fields = ('name',)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'num_pages', 'created_at', 'updated_at')
    search_fields = ('title',)

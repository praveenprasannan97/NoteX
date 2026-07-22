from django.conf import settings
from django.db import models


class Category(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class Note(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=255, default='Untitled Note')

    content1 = models.TextField(blank=True, default='')
    content2 = models.TextField(blank=True, default='')
    content3 = models.TextField(blank=True, default='')
    content4 = models.TextField(blank=True, default='')
    content5 = models.TextField(blank=True, default='')
    content6 = models.TextField(blank=True, default='')
    content7 = models.TextField(blank=True, default='')
    content8 = models.TextField(blank=True, default='')
    content9 = models.TextField(blank=True, default='')
    content10 = models.TextField(blank=True, default='')
    num_pages = models.PositiveSmallIntegerField(default=1)

    # Stored as plain text (NOT a foreign key) so deleting a category
    # never cascades into notes / breaks note data.
    category = models.CharField(max_length=100, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

    def get_page_content(self, page_number):
        return getattr(self, f'content{page_number}', '')

    def set_page_content(self, page_number, value):
        setattr(self, f'content{page_number}', value)

    def all_pages(self):
        return [self.get_page_content(i) for i in range(1, self.num_pages + 1)]

    def search_blob(self):
        parts = [self.title, self.category] + self.all_pages()
        return ' '.join(parts)

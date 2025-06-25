from django.contrib import admin
from .models import Game


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """游戏管理界面"""
    
    list_display = [
        'name', 'steam_id', 'price', 'currency', 'discount_percent',
        'developer', 'release_date', 'is_free', 'is_new', 'scraped_at'
    ]
    list_filter = [
        'is_free', 'is_new', 'currency', 'platforms', 'release_date', 'scraped_at'
    ]
    search_fields = ['name', 'steam_id', 'developer', 'publisher']
    readonly_fields = ['steam_id', 'created_at', 'updated_at', 'scraped_at']
    list_per_page = 50
    
    fieldsets = (
        ('基础信息', {
            'fields': ('steam_id', 'name', 'description')
        }),
        ('价格信息', {
            'fields': ('price', 'currency', 'discount_percent', 'is_free')
        }),
        ('媒体信息', {
            'fields': ('header_image', 'screenshots')
        }),
        ('游戏详情', {
            'fields': ('developer', 'publisher', 'release_date', 'tags', 'platforms', 'languages')
        }),
        ('评分信息', {
            'fields': ('review_score', 'review_count')
        }),
        ('状态信息', {
            'fields': ('is_new',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at', 'scraped_at'),
            'classes': ('collapse',)
        }),
    ) 
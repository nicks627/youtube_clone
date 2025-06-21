from django.contrib import admin
from .models import Video, Channel, Subscription, SubscriptionFolder

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'uploaded_by', 'uploaded_at', 'views']
    list_filter = ['uploaded_at', 'uploaded_by']
    search_fields = ['title', 'description']
    readonly_fields = ['views', 'uploaded_at']

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'subscriber_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = ['created_at', 'subscriber_count']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['subscriber', 'channel', 'folder', 'subscribed_at', 'notifications_enabled']
    list_filter = ['subscribed_at', 'notifications_enabled', 'folder']
    search_fields = ['subscriber__username', 'channel__name']
    readonly_fields = ['subscribed_at']

@admin.register(SubscriptionFolder)
class SubscriptionFolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'color', 'order', 'created_at']
    list_filter = ['created_at', 'user']
    search_fields = ['name', 'user__username']
    readonly_fields = ['created_at']

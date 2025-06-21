from django.urls import path
from . import views

urlpatterns = [
    path('', views.video_list, name='video_list'),
    path('video/<int:pk>/', views.video_detail, name='video_detail'),
    path('upload/', views.upload_video, name='upload_video'),
    path('signup/', views.signup, name='signup'),
    
    # Genre filtering
    path('genre/<str:genre>/', views.video_list_by_genre, name='video_list_by_genre'),
    
    # Subscription management
    path('api/toggle-subscription/', views.toggle_subscription, name='toggle_subscription'),
    path('subscriptions/', views.subscriptions_list, name='subscriptions'),
    path('subscriptions/manage/', views.subscriptions_manage, name='subscriptions_manage'),
    
    # Folder management
    path('api/folders/create/', views.create_folder, name='create_folder'),
    path('api/folders/<int:folder_id>/edit/', views.edit_folder, name='edit_folder'),
    path('api/folders/<int:folder_id>/delete/', views.delete_folder, name='delete_folder'),
    path('api/subscriptions/move/', views.move_subscription_to_folder, name='move_subscription_to_folder'),
    
    # Account settings
    path('settings/', views.account_settings, name='account_settings'),
    
    # Main pages
    path('explore/', views.explore, name='explore'),
    path('shorts/', views.shorts, name='shorts'),
    path('history/', views.history, name='history'),
    path('watch-later/', views.watch_later_list, name='watch_later'),
    path('trending/', views.trending, name='trending'),
    
    # Watch later API
    path('api/watch-later/toggle/', views.toggle_watch_later, name='toggle_watch_later'),
    
    # History management API
    path('api/history/clear/', views.clear_watch_history, name='clear_watch_history'),
    path('api/history/remove/', views.remove_history_item, name='remove_history_item'),
    
    # Search
    path('search/', views.search_videos, name='search_videos'),
    
    # Comments and likes
    path('api/comments/', views.get_comments, name='get_comments'),
    path('api/comments/add/', views.add_comment, name='add_comment'),
    path('api/comments/delete/', views.delete_comment, name='delete_comment'),
    path('api/videos/like/', views.toggle_video_like, name='toggle_video_like'),
    
    # User content pages
    path('your-videos/', views.your_videos, name='your_videos'),
    path('liked-videos/', views.liked_videos, name='liked_videos'),
    
    # Channel pages
    path('channel/<str:username>/', views.channel_detail, name='channel_detail'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Payment and monetization
    path('settings/payments/', views.payment_settings, name='payment_settings'),
    path('api/payments/donation/', views.process_donation_payment, name='process_donation'),
    path('api/payments/purchase/', views.process_content_purchase, name='process_purchase'),
    path('payments/callback/', views.payment_callback, name='payment_callback'),
    path('my-purchases/', views.my_purchases, name='my_purchases'),
    
    # Notifications
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.core.paginator import Paginator
import os
import json
from .models import Video, Channel, Subscription, SubscriptionFolder, UserSettings, WatchHistory, WatchLater, Comment, VideoLike, PaymentSettings, PaidContent, Purchase, Donation
from .forms import VideoUploadForm
from .notification_service import NotificationService
from .search_utils import SearchEnhancer, SearchHistory

def video_list(request):
    # Get regular videos (exclude shorts)
    videos_list = Video.objects.select_related('uploaded_by').prefetch_related('likes').filter(is_shorts=False)
    
    # Get shorts videos for the shorts section
    shorts_videos = Video.objects.select_related('uploaded_by').filter(is_shorts=True).order_by('-uploaded_at')[:6]
    
    # Pagination for regular videos
    paginator = Paginator(videos_list, 12)  # Show 12 videos per page
    page_number = request.GET.get('page')
    videos = paginator.get_page(page_number)
    
    context = {
        'videos': videos,
        'shorts_videos': shorts_videos,
        'is_paginated': videos.has_other_pages(),
        'page_obj': videos,
    }
    
    # Simplified sidebar context to avoid recursion
    if request.user.is_authenticated:
        context['user_subscriptions_without_folder'] = []
        context['user_subscriptions_by_folder'] = {}
    
    return render(request, 'videos/video_list.html', context)

def get_sidebar_context(user):
    """Get subscription data for sidebar"""
    subscriptions = Subscription.objects.filter(subscriber=user).select_related('channel', 'folder')
    folders = SubscriptionFolder.objects.filter(user=user)
    
    # Group subscriptions by folder
    subscriptions_by_folder = {}
    subscriptions_without_folder = []
    
    for subscription in subscriptions:
        if subscription.folder:
            if subscription.folder not in subscriptions_by_folder:
                subscriptions_by_folder[subscription.folder] = []
            subscriptions_by_folder[subscription.folder].append(subscription)
        else:
            subscriptions_without_folder.append(subscription)
    
    return {
        'user_subscriptions_by_folder': subscriptions_by_folder,
        'user_subscriptions_without_folder': subscriptions_without_folder[:5],  # Limit to 5 for sidebar
        'user_subscription_folders': folders
    }

def video_detail(request, pk):
    try:
        video = get_object_or_404(Video, pk=pk)
        
        # Skip file existence check for testing
        if video.video_file and hasattr(video.video_file, 'path'):
            if not os.path.exists(video.video_file.path):
                return render(request, 'videos/error.html', {
                    'error_title': '動画ファイルが見つかりません',
                    'error_message': 'この動画のファイルが削除されているか、アクセスできません。',
                    'show_back_button': True
                })
        
        video.views += 1
        video.save()
        
        # Add to watch history if user is authenticated
        if request.user.is_authenticated:
            WatchHistory.objects.update_or_create(
                user=request.user,
                video=video,
                defaults={'watched_at': timezone.now()}
            )
        
        # Get channel information (with caching)
        channel_cache_key = f'channel_{video.uploaded_by.id}'
        channel = cache.get(channel_cache_key)
        if channel is None:
            channel, created = Channel.objects.get_or_create(
                user=video.uploaded_by,
                defaults={
                    'name': video.uploaded_by.username,
                    'description': f'{video.uploaded_by.username}のチャンネル'
                }
            )
            cache_timeout = getattr(settings, 'CACHE_TIMEOUTS', {}).get('channel_stats', 300)
            cache.set(channel_cache_key, channel, cache_timeout)
        
        # Get user's default playback speed
        user_settings = None
        default_speed = 1.0
        if request.user.is_authenticated:
            user_settings, created = UserSettings.objects.get_or_create(user=request.user)
            default_speed = user_settings.default_playback_speed
        
        # Check if user is subscribed to this channel
        is_subscribed = False
        subscription = None
        if request.user.is_authenticated:
            try:
                subscription = Subscription.objects.get(
                    subscriber=request.user,
                    channel=channel
                )
                is_subscribed = True
            except Subscription.DoesNotExist:
                pass
        
        related_videos = Video.objects.select_related('uploaded_by').exclude(pk=pk).order_by('-uploaded_at')[:5]
        
        # Get comments for this video
        comments = Comment.objects.filter(video=video, parent=None).select_related('user')
        
        # Get user's like status for this video
        user_like = None
        if request.user.is_authenticated:
            try:
                user_like = VideoLike.objects.get(user=request.user, video=video)
            except VideoLike.DoesNotExist:
                pass
        
        # Check if user has purchased this video (for paid content)
        has_purchased = False
        if request.user.is_authenticated and video.is_paid:
            has_purchased = Purchase.objects.filter(
                user=request.user,
                paid_content__video=video,
                status='completed'
            ).exists()
        
        # Check if user can view the video
        can_view_video = True
        if video.is_paid and request.user.is_authenticated:
            can_view_video = (video.uploaded_by == request.user) or has_purchased
        elif video.is_paid and not request.user.is_authenticated:
            can_view_video = False
        
        context = {
            'video': video,
            'channel': channel,
            'is_subscribed': is_subscribed,
            'subscription': subscription,
            'related_videos': related_videos,
            'default_playback_speed': default_speed,
            'comments': comments,
            'user_like': user_like,
            'has_purchased': has_purchased,
            'can_view_video': can_view_video,
        }
        
        # Add subscription data for sidebar
        if request.user.is_authenticated:
            context.update(get_sidebar_context(request.user))
        
        return render(request, 'videos/video_detail.html', context)
    except Exception as e:
        return render(request, 'videos/error.html', {
            'error_title': 'エラーが発生しました',
            'error_message': '動画の読み込み中にエラーが発生しました。しばらく経ってから再度お試しください。',
            'show_back_button': True
        })

@login_required
def upload_video(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                video = form.save(commit=False)
                video.uploaded_by = request.user
                video.save()
                
                # 新しい動画の通知を送信
                NotificationService.notify_new_video(video)
                
                messages.success(request, '動画のアップロードが完了しました！')
                return redirect('video_list')
            except Exception as e:
                messages.error(request, f'アップロード中にエラーが発生しました: {str(e)}')
        else:
            # フォームエラーがある場合
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form.fields[field].label if field in form.fields else field}: {error}')
    else:
        form = VideoUploadForm()
    context = {'form': form}
    
    # Add subscription data for sidebar
    if request.user.is_authenticated:
        context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/upload.html', context)

@login_required
@require_POST
def toggle_subscription(request):
    try:
        data = json.loads(request.body)
        channel_id = data.get('channel_id')
        
        if not channel_id:
            return JsonResponse({'error': 'チャンネルIDが必要です'}, status=400)
        
        channel = get_object_or_404(Channel, id=channel_id)
        
        # Cannot subscribe to own channel
        if channel.user == request.user:
            return JsonResponse({'error': '自分のチャンネルには登録できません'}, status=400)
        
        subscription, created = Subscription.objects.get_or_create(
            subscriber=request.user,
            channel=channel
        )
        
        if created:
            # New subscription
            channel.subscriber_count += 1
            channel.save()
            subscribed = True
            message = f'{channel.name}に登録しました'
            
            # 新しいチャンネル登録の通知を送信
            NotificationService.notify_new_subscription(subscription)
        else:
            # Unsubscribe
            subscription.delete()
            channel.subscriber_count = max(0, channel.subscriber_count - 1)
            channel.save()
            subscribed = False
            message = f'{channel.name}の登録を解除しました'
        
        return JsonResponse({
            'subscribed': subscribed,
            'subscriber_count': channel.get_subscriber_count_display(),
            'message': message
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def subscriptions_manage(request):
    # Get all user's subscriptions
    subscriptions = Subscription.objects.filter(subscriber=request.user).select_related('channel', 'folder')
    
    # Get all user's folders
    folders = SubscriptionFolder.objects.filter(user=request.user)
    
    # Group subscriptions by folder
    subscriptions_by_folder = {}
    subscriptions_without_folder = []
    
    for subscription in subscriptions:
        if subscription.folder:
            if subscription.folder not in subscriptions_by_folder:
                subscriptions_by_folder[subscription.folder] = []
            subscriptions_by_folder[subscription.folder].append(subscription)
        else:
            subscriptions_without_folder.append(subscription)
    
    return render(request, 'videos/subscriptions_manage.html', {
        'subscriptions_by_folder': subscriptions_by_folder,
        'subscriptions_without_folder': subscriptions_without_folder,
        'folders': folders,
    })

@login_required
def subscriptions_list(request):
    # Get user's subscriptions
    subscriptions = Subscription.objects.filter(subscriber=request.user).select_related('channel')
    
    # Get recommended channels if user has no subscriptions
    recommended_channels = []
    if not subscriptions.exists():
        # Get channels with most subscribers (excluding user's own channel)
        recommended_channels = Channel.objects.exclude(user=request.user).order_by('-subscriber_count')[:6]
    
    # Get recent videos from subscribed channels
    subscribed_videos = []
    if subscriptions.exists():
        subscribed_channel_ids = [sub.channel.id for sub in subscriptions]
        subscribed_videos = Video.objects.select_related('uploaded_by').filter(
            uploaded_by__channel__id__in=subscribed_channel_ids
        ).order_by('-uploaded_at')[:12]
    
    context = {
        'subscriptions': subscriptions,
        'recommended_channels': recommended_channels,
        'subscribed_videos': subscribed_videos,
    }
    
    # Add subscription data for sidebar
    context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/subscriptions_list.html', context)

@login_required
@require_POST
def create_folder(request):
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        color = data.get('color', '#ff0000')
        
        if not name:
            return JsonResponse({'error': 'フォルダー名が必要です'}, status=400)
        
        if len(name) > 50:
            return JsonResponse({'error': 'フォルダー名は50文字以内で入力してください'}, status=400)
        
        # Check if folder with same name exists
        if SubscriptionFolder.objects.filter(user=request.user, name=name).exists():
            return JsonResponse({'error': 'そのフォルダー名は既に存在します'}, status=400)
        
        folder = SubscriptionFolder.objects.create(
            user=request.user,
            name=name,
            color=color,
            order=SubscriptionFolder.objects.filter(user=request.user).count()
        )
        
        return JsonResponse({
            'id': folder.id,
            'name': folder.name,
            'color': folder.color,
            'message': f'フォルダー "{name}" を作成しました'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def edit_folder(request, folder_id):
    try:
        folder = get_object_or_404(SubscriptionFolder, id=folder_id, user=request.user)
        
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        color = data.get('color', folder.color)
        
        if not name:
            return JsonResponse({'error': 'フォルダー名が必要です'}, status=400)
        
        if len(name) > 50:
            return JsonResponse({'error': 'フォルダー名は50文字以内で入力してください'}, status=400)
        
        # Check if folder with same name exists (excluding current folder)
        if SubscriptionFolder.objects.filter(user=request.user, name=name).exclude(id=folder_id).exists():
            return JsonResponse({'error': 'そのフォルダー名は既に存在します'}, status=400)
        
        folder.name = name
        folder.color = color
        folder.save()
        
        return JsonResponse({
            'id': folder.id,
            'name': folder.name,
            'color': folder.color,
            'message': f'フォルダー "{name}" を更新しました'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def delete_folder(request, folder_id):
    try:
        folder = get_object_or_404(SubscriptionFolder, id=folder_id, user=request.user)
        
        # Move all subscriptions in this folder to no folder
        Subscription.objects.filter(folder=folder).update(folder=None)
        
        folder_name = folder.name
        folder.delete()
        
        return JsonResponse({
            'message': f'フォルダー "{folder_name}" を削除しました'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def move_subscription_to_folder(request):
    try:
        data = json.loads(request.body)
        subscription_id = data.get('subscription_id')
        folder_id = data.get('folder_id')
        
        subscription = get_object_or_404(Subscription, id=subscription_id, subscriber=request.user)
        
        if folder_id:
            folder = get_object_or_404(SubscriptionFolder, id=folder_id, user=request.user)
            subscription.folder = folder
            message = f'{subscription.channel.name}を{folder.name}に移動しました'
        else:
            subscription.folder = None
            message = f'{subscription.channel.name}をフォルダーから移動しました'
        
        subscription.save()
        
        return JsonResponse({'message': message})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'アカウントが作成され、ログインしました！')
            return redirect('video_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


def video_list_by_genre(request, genre):
    # Validate genre
    valid_genres = [choice[0] for choice in Video.GENRE_CHOICES]
    if genre not in valid_genres:
        return redirect('video_list')
    
    # Get genre display name
    genre_display = dict(Video.GENRE_CHOICES).get(genre, genre)
    
    videos_list = Video.objects.select_related('uploaded_by').filter(genre=genre)
    
    # Pagination
    paginator = Paginator(videos_list, 12)  # Show 12 videos per page
    page_number = request.GET.get('page')
    videos = paginator.get_page(page_number)
    
    context = {
        'videos': videos,
        'current_genre': genre,
        'genre_display': genre_display,
        'is_paginated': videos.has_other_pages(),
        'page_obj': videos,
    }
    
    # Add subscription data for sidebar
    if request.user.is_authenticated:
        context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/video_list.html', context)

@login_required
def account_settings(request):
    settings, created = UserSettings.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        if 'update_playback_speed' in request.POST:
            # Update playback speed
            speed = float(request.POST.get('default_playback_speed', 1.0))
            settings.default_playback_speed = speed
            settings.save()
            messages.success(request, 'デフォルト再生速度を更新しました')
            return redirect('account_settings')
        
        elif 'delete_account' in request.POST:
            # Confirm account deletion
            confirm_username = request.POST.get('confirm_username', '')
            if confirm_username == request.user.username:
                # Delete all user data
                user = request.user
                user.delete()
                messages.success(request, 'アカウントが削除されました')
                return redirect('video_list')
            else:
                messages.error(request, 'ユーザー名が一致しません。アカウント削除をキャンセルしました。')
    
    context = {
        'settings': settings,
        'playback_speed_choices': UserSettings._meta.get_field('default_playback_speed').choices
    }
    
    # Add subscription data for sidebar
    if request.user.is_authenticated:
        context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/account_settings.html', context)

def explore(request):
    # Try to get cached data first
    cache_timeout = getattr(settings, 'CACHE_TIMEOUTS', {}).get('trending_videos', 600)
    
    trending_videos = cache.get('explore_trending_videos')
    if trending_videos is None:
        trending_videos = list(Video.objects.select_related('uploaded_by').filter(genre='trending', is_shorts=False).order_by('-views', '-uploaded_at')[:12])
        cache.set('explore_trending_videos', trending_videos, cache_timeout)
    
    music_videos = cache.get('explore_music_videos')
    if music_videos is None:
        music_videos = list(Video.objects.select_related('uploaded_by').filter(genre='music', is_shorts=False).order_by('-views', '-uploaded_at')[:8])
        cache.set('explore_music_videos', music_videos, cache_timeout)
    
    gaming_videos = cache.get('explore_gaming_videos')
    if gaming_videos is None:
        gaming_videos = list(Video.objects.select_related('uploaded_by').filter(genre='gaming', is_shorts=False).order_by('-views', '-uploaded_at')[:8])
        cache.set('explore_gaming_videos', gaming_videos, cache_timeout)
    
    news_videos = cache.get('explore_news_videos')
    if news_videos is None:
        news_videos = list(Video.objects.select_related('uploaded_by').filter(genre='news', is_shorts=False).order_by('-uploaded_at')[:8])
        cache.set('explore_news_videos', news_videos, cache_timeout)
    
    # Get most viewed videos overall (exclude shorts)
    popular_cache_timeout = getattr(settings, 'CACHE_TIMEOUTS', {}).get('popular_videos', 900)
    popular_videos = cache.get('explore_popular_videos')
    if popular_videos is None:
        popular_videos = list(Video.objects.select_related('uploaded_by').filter(is_shorts=False).order_by('-views')[:16])
        cache.set('explore_popular_videos', popular_videos, popular_cache_timeout)
    
    context = {
        'trending_videos': trending_videos,
        'music_videos': music_videos,
        'gaming_videos': gaming_videos,
        'news_videos': news_videos,
        'popular_videos': popular_videos,
    }
    
    # Simplified sidebar context to avoid recursion
    if request.user.is_authenticated:
        context['user_subscriptions_without_folder'] = []
        context['user_subscriptions_by_folder'] = {}
    
    return render(request, 'videos/explore.html', context)

def shorts(request):
    # Get shorts videos (60 seconds or less)
    shorts_videos = Video.objects.filter(is_shorts=True).select_related('uploaded_by').order_by('-uploaded_at')
    
    context = {
        'shorts_videos': shorts_videos,
    }
    
    # Add subscription data for sidebar
    if request.user.is_authenticated:
        context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/shorts.html', context)

@login_required
def history(request):
    # Get user's watch history
    history_items = WatchHistory.objects.filter(user=request.user).select_related('video', 'video__uploaded_by')
    
    context = {
        'history_items': history_items,
    }
    
    # Add subscription data for sidebar
    context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/history.html', context)

@login_required
def watch_later_list(request):
    # Get user's watch later list
    watch_later_items = WatchLater.objects.filter(user=request.user).select_related('video', 'video__uploaded_by')
    
    context = {
        'watch_later_items': watch_later_items,
    }
    
    # Add subscription data for sidebar
    context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/watch_later.html', context)

@login_required
@require_POST
def toggle_watch_later(request):
    try:
        data = json.loads(request.body)
        video_id = data.get('video_id')
        
        if not video_id:
            return JsonResponse({'error': '動画IDが必要です'}, status=400)
        
        video = get_object_or_404(Video, id=video_id)
        
        watch_later_item, created = WatchLater.objects.get_or_create(
            user=request.user,
            video=video
        )
        
        if created:
            # Added to watch later
            message = '後で見るに追加しました'
            in_watch_later = True
        else:
            # Remove from watch later
            watch_later_item.delete()
            message = '後で見るから削除しました'
            in_watch_later = False
        
        return JsonResponse({
            'in_watch_later': in_watch_later,
            'message': message
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def clear_watch_history(request):
    """すべての視聴履歴をクリアする"""
    try:
        # ユーザーの全ての視聴履歴を削除
        deleted_count = WatchHistory.objects.filter(user=request.user).delete()[0]
        
        return JsonResponse({
            'success': True,
            'message': f'{deleted_count}件の視聴履歴を削除しました',
            'deleted_count': deleted_count
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def remove_history_item(request):
    """個別の視聴履歴アイテムを削除する"""
    try:
        data = json.loads(request.body)
        history_id = data.get('history_id')
        
        if not history_id:
            return JsonResponse({'error': '履歴IDが必要です'}, status=400)
        
        # 指定された履歴アイテムを削除（ユーザー確認付き）
        history_item = get_object_or_404(WatchHistory, id=history_id, user=request.user)
        video_title = history_item.video.title
        history_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'「{video_title}」を履歴から削除しました'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def trending(request):
    # Try to get cached trending videos first
    cache_timeout = getattr(settings, 'CACHE_TIMEOUTS', {}).get('trending_videos', 600)
    trending_videos = cache.get('trending_page_videos')
    
    if trending_videos is None:
        # Get trending videos (videos with most views in the last week or overall trending genre)
        from datetime import datetime, timedelta
        
        # Get videos from the last month with high view counts
        last_month = datetime.now() - timedelta(days=30)
        trending_videos = Video.objects.select_related('uploaded_by').filter(
            uploaded_at__gte=last_month
        ).order_by('-views', '-uploaded_at')[:24]
        
        # If not enough videos from last month, get trending genre videos
        if trending_videos.count() < 12:
            trending_videos = Video.objects.select_related('uploaded_by').filter(
                genre='trending'
            ).order_by('-views', '-uploaded_at')[:24]
        
        # If still not enough, get most viewed videos overall
        if trending_videos.count() < 12:
            trending_videos = Video.objects.select_related('uploaded_by').order_by('-views', '-uploaded_at')[:24]
        
        # Convert to list and cache
        trending_videos = list(trending_videos)
        cache.set('trending_page_videos', trending_videos, cache_timeout)
    
    context = {
        'trending_videos': trending_videos,
    }
    
    # Add subscription data for sidebar
    if request.user.is_authenticated:
        context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/trending.html', context)

def search_videos(request):
    query = request.GET.get('q', '').strip()
    
    if not query:
        return redirect('video_list')
    
    # Add to search history
    if request.user.is_authenticated:
        SearchHistory.add_search(request, query)
    
    # Get filters from request
    filters = {
        'sort_by': request.GET.get('sort_by', 'relevance'),
        'upload_date': request.GET.get('upload_date'),
        'duration': request.GET.get('duration'),
        'type': request.GET.get('type'),
        'genre': request.GET.get('genre'),
    }
    
    # Remove empty filters
    filters = {k: v for k, v in filters.items() if v}
    
    # Enhanced search with filters
    videos_list = SearchEnhancer.search_videos(query, filters)
    
    # Pagination
    paginator = Paginator(videos_list, 12)  # Show 12 results per page
    page_number = request.GET.get('page')
    videos = paginator.get_page(page_number)
    
    # Get search history and trending searches
    search_history = SearchHistory.get_history(request) if request.user.is_authenticated else []
    trending_searches = SearchEnhancer.get_trending_searches(5)
    
    context = {
        'videos': videos,
        'search_query': query,
        'results_count': paginator.count,
        'is_paginated': videos.has_other_pages(),
        'page_obj': videos,
        'filters': filters,
        'sort_options': SearchEnhancer.SORT_OPTIONS,
        'upload_date_filters': SearchEnhancer.UPLOAD_DATE_FILTERS,
        'duration_filters': SearchEnhancer.DURATION_FILTERS,
        'search_history': search_history,
        'trending_searches': trending_searches,
    }
    
    # Add subscription data for sidebar
    if request.user.is_authenticated:
        context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/search_results.html', context)

@login_required
def search_suggestions(request):
    """Get search suggestions based on query"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'suggestions': []})
    
    try:
        # Get search suggestions from SearchEnhancer
        suggestions = SearchEnhancer.get_search_suggestions(query)
        
        # Also get user's recent search history that matches the query
        if request.user.is_authenticated:
            search_history = SearchHistory.get_history(request)
            # Filter history items that start with the query
            history_suggestions = [
                item for item in search_history 
                if item.lower().startswith(query.lower())
            ][:3]  # Limit to 3 history suggestions
            
            # Combine and deduplicate suggestions
            all_suggestions = list(dict.fromkeys(history_suggestions + suggestions))[:10]
        else:
            all_suggestions = suggestions[:10]
        
        return JsonResponse({
            'suggestions': all_suggestions,
            'query': query
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def clear_search_history(request):
    """Clear user's search history"""
    try:
        # Clear search history for the authenticated user
        SearchHistory.clear_history(request)
        
        return JsonResponse({
            'success': True,
            'message': '検索履歴を削除しました'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_comments(request):
    """動画のコメントを取得するAPI"""
    video_id = request.GET.get('video_id')
    
    if not video_id:
        return JsonResponse({'error': '動画IDが必要です'}, status=400)
    
    try:
        video = get_object_or_404(Video, id=video_id)
        comments = Comment.objects.filter(video=video, parent=None).order_by('-created_at')
        
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'text': comment.content,
                'user_name': comment.user.username,
                'created_at': comment.created_at.strftime('%Y年%m月%d日 %H:%M'),
                'is_reply': comment.is_reply
            })
        
        return JsonResponse({
            'success': True,
            'comments': comments_data
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def add_comment(request):
    try:
        data = json.loads(request.body)
        video_id = data.get('video_id')
        content = data.get('content', '').strip()
        parent_id = data.get('parent_id')
        
        if not video_id or not content:
            return JsonResponse({'error': '動画IDとコメント内容が必要です'}, status=400)
        
        video = get_object_or_404(Video, id=video_id)
        
        parent_comment = None
        if parent_id:
            parent_comment = get_object_or_404(Comment, id=parent_id, video=video)
        
        comment = Comment.objects.create(
            video=video,
            user=request.user,
            content=content,
            parent=parent_comment
        )
        
        # 新しいコメントの通知を送信
        NotificationService.notify_new_comment(comment)
        
        return JsonResponse({
            'success': True,
            'id': comment.id,
            'content': comment.content,
            'username': comment.user.username,
            'created_at': comment.created_at.strftime('%Y年%m月%d日 %H:%M'),
            'is_reply': comment.is_reply,
            'message': 'コメントを投稿しました'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def toggle_video_like(request):
    try:
        data = json.loads(request.body)
        video_id = data.get('video_id')
        like_type = data.get('like_type')  # 1 for like, -1 for dislike
        
        if not video_id or like_type not in [1, -1]:
            return JsonResponse({'error': '無効なパラメータです'}, status=400)
        
        video = get_object_or_404(Video, id=video_id)
        
        # Check if user already liked/disliked this video
        existing_like = VideoLike.objects.filter(user=request.user, video=video).first()
        
        if existing_like:
            if existing_like.like_type == like_type:
                # Remove the like/dislike
                existing_like.delete()
                liked = False
                message = '評価を取り消しました'
            else:
                # Change like to dislike or vice versa
                existing_like.like_type = like_type
                existing_like.save()
                liked = True
                message = '高評価しました' if like_type == 1 else '低評価しました'
        else:
            # Create new like/dislike
            video_like = VideoLike.objects.create(
                user=request.user,
                video=video,
                like_type=like_type
            )
            liked = True
            message = '高評価しました' if like_type == 1 else '低評価しました'
            
            # 新しい高評価の通知を送信
            NotificationService.notify_new_like(video_like)
        
        return JsonResponse({
            'success': True,
            'liked': liked if like_type == 1 else False,
            'disliked': liked if like_type == -1 else False,
            'like_type': like_type,
            'like_count': video.get_like_count(),
            'dislike_count': video.get_dislike_count(),
            'message': message
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def your_videos(request):
    # Get user's uploaded videos
    videos_list = Video.objects.select_related('uploaded_by').filter(uploaded_by=request.user).order_by('-uploaded_at')
    
    # Pagination
    paginator = Paginator(videos_list, 12)  # Show 12 videos per page
    page_number = request.GET.get('page')
    videos = paginator.get_page(page_number)
    
    context = {
        'videos': videos,
        'total_videos': paginator.count,
        'total_views': sum(video.views for video in videos_list),
        'is_paginated': videos.has_other_pages(),
        'page_obj': videos,
    }
    
    # Add subscription data for sidebar
    context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/your_videos.html', context)

@login_required
def liked_videos(request):
    # Get videos liked by the user
    liked_video_ids = VideoLike.objects.filter(user=request.user, like_type=1).values_list('video_id', flat=True)
    videos_list = Video.objects.filter(id__in=liked_video_ids).select_related('uploaded_by').order_by('-uploaded_at')
    
    # Pagination
    paginator = Paginator(videos_list, 12)  # Show 12 videos per page
    page_number = request.GET.get('page')
    videos = paginator.get_page(page_number)
    
    context = {
        'videos': videos,
        'total_liked': paginator.count,
        'is_paginated': videos.has_other_pages(),
        'page_obj': videos,
    }
    
    # Add subscription data for sidebar
    context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/liked_videos.html', context)

@login_required
@require_POST
def delete_comment(request):
    try:
        data = json.loads(request.body)
        comment_id = data.get('comment_id')
        
        if not comment_id:
            return JsonResponse({'error': 'コメントIDが必要です'}, status=400)
        
        comment = get_object_or_404(Comment, id=comment_id)
        
        # Check if user owns the comment
        if comment.user != request.user:
            return JsonResponse({'error': '自分のコメントのみ削除できます'}, status=403)
        
        comment.delete()
        
        return JsonResponse({
            'message': 'コメントを削除しました'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def channel_detail(request, username):
    # Get the user and their channel
    channel_user = get_object_or_404(User, username=username)
    channel = get_object_or_404(Channel, user=channel_user)
    
    # Get channel's videos
    videos_list = Video.objects.select_related('uploaded_by').filter(uploaded_by=channel_user).order_by('-uploaded_at')
    
    # Pagination
    paginator = Paginator(videos_list, 12)  # Show 12 videos per page
    page_number = request.GET.get('page')
    videos = paginator.get_page(page_number)
    
    # Check if current user is subscribed to this channel
    is_subscribed = False
    if request.user.is_authenticated:
        is_subscribed = Subscription.objects.filter(
            subscriber=request.user,
            channel=channel
        ).exists()
    
    # Calculate channel statistics
    total_views = sum(video.views for video in videos_list)
    total_videos = paginator.count
    
    context = {
        'channel': channel,
        'channel_user': channel_user,
        'videos': videos,
        'is_subscribed': is_subscribed,
        'total_views': total_views,
        'total_videos': total_videos,
        'is_paginated': videos.has_other_pages(),
        'page_obj': videos,
    }
    
    # Add subscription data for sidebar
    if request.user.is_authenticated:
        context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/channel_detail.html', context)

@login_required
def edit_profile(request):
    channel, created = Channel.objects.get_or_create(
        user=request.user,
        defaults={
            'name': request.user.username,
            'description': f'{request.user.username}のチャンネル'
        }
    )
    
    if request.method == 'POST':
        # Update channel information
        channel.name = request.POST.get('name', channel.name)
        channel.bio = request.POST.get('bio', '')
        channel.website = request.POST.get('website', '')
        channel.twitter_handle = request.POST.get('twitter_handle', '')
        
        # Handle avatar upload
        if 'avatar' in request.FILES:
            channel.avatar = request.FILES['avatar']
        
        # Handle banner upload
        if 'banner' in request.FILES:
            channel.banner = request.FILES['banner']
        
        channel.save()
        messages.success(request, 'プロフィールを更新しました')
        return redirect('edit_profile')
    
    context = {
        'channel': channel,
    }
    
    # Add subscription data for sidebar
    context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/edit_profile.html', context)

@login_required
def payment_settings(request):
    payment_settings, created = PaymentSettings.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        payment_settings.link_api_key = request.POST.get('link_api_key', '')
        payment_settings.link_secret_key = request.POST.get('link_secret_key', '')
        payment_settings.is_payments_enabled = 'enable_payments' in request.POST
        payment_settings.save()
        
        messages.success(request, '決済設定を更新しました')
        return redirect('payment_settings')
    
    context = {
        'payment_settings': payment_settings,
    }
    
    # Add subscription data for sidebar
    context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/payment_settings.html', context)

@login_required
@require_POST
def process_donation_payment(request):
    from .payment_service import get_payment_service
    
    try:
        data = json.loads(request.body)
        video_id = data.get('video_id')
        amount = data.get('amount')
        message = data.get('message', '')
        
        if not video_id or not amount:
            return JsonResponse({'error': '動画IDと金額が必要です'}, status=400)
        
        video = get_object_or_404(Video, id=video_id)
        to_user = video.uploaded_by
        
        if to_user == request.user:
            return JsonResponse({'error': '自分の動画には投げ銭できません'}, status=400)
        
        # Get payment service for the recipient
        payment_service = get_payment_service(to_user)
        if not payment_service:
            return JsonResponse({'error': 'このクリエイターは投げ銭を受け付けていません'}, status=400)
        
        # Process donation
        donation, payment_response = payment_service.process_donation(
            from_user=request.user,
            to_user=to_user,
            amount=amount,
            message=message,
            video=video
        )
        
        return JsonResponse({
            'success': True,
            'payment_url': payment_response.get('payment_url'),
            'donation_id': donation.id,
            'message': '決済ページにリダイレクトします'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def process_content_purchase(request):
    from .payment_service import get_payment_service
    
    try:
        data = json.loads(request.body)
        video_id = data.get('video_id')
        
        if not video_id:
            return JsonResponse({'error': '動画IDが必要です'}, status=400)
        
        video = get_object_or_404(Video, id=video_id)
        
        if not video.is_paid:
            return JsonResponse({'error': 'この動画は無料です'}, status=400)
        
        # Get payment service for the content creator
        payment_service = get_payment_service(video.uploaded_by)
        if not payment_service:
            return JsonResponse({'error': 'この動画の購入は現在利用できません'}, status=400)
        
        # Create paid content if it doesn't exist
        paid_content, created = PaidContent.objects.get_or_create(
            video=video,
            defaults={
                'channel': video.uploaded_by.channel,
                'title': video.title,
                'description': video.description,
                'price': video.price,
                'content_type': 'video'
            }
        )
        
        # Process purchase
        purchase, payment_response = payment_service.process_content_purchase(
            user=request.user,
            paid_content=paid_content
        )
        
        return JsonResponse({
            'success': True,
            'payment_url': payment_response.get('payment_url'),
            'purchase_id': purchase.id,
            'message': '決済ページにリダイレクトします'
        })
    
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def payment_callback(request):
    """
    Handle payment completion callbacks from Link
    """
    from .payment_service import LinkPaymentService
    
    payment_id = request.GET.get('payment_id')
    status = request.GET.get('status', 'completed')
    
    if not payment_id:
        return redirect('video_list')
    
    # Handle the callback
    service = LinkPaymentService()
    success = service.handle_payment_callback(payment_id, status)
    
    if success and status == 'completed':
        messages.success(request, '支払いが完了しました！')
    elif status == 'failed':
        messages.error(request, '支払いに失敗しました')
    
    return redirect('video_list')

@login_required
def my_purchases(request):
    purchases = Purchase.objects.filter(user=request.user).select_related('paid_content', 'paid_content__video')
    
    context = {
        'purchases': purchases,
    }
    
    # Add subscription data for sidebar
    context.update(get_sidebar_context(request.user))
    
    return render(request, 'videos/my_purchases.html', context)

@login_required
def get_notifications(request):
    """通知一覧を取得"""
    try:
        notifications = NotificationService.get_user_notifications(request.user)
        unread_count = NotificationService.get_unread_count(request.user)
        
        return JsonResponse({
            'notifications': notifications,
            'unread_count': unread_count
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def mark_notification_read(request):
    """通知を既読にする"""
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        if not notification_id:
            return JsonResponse({'error': '通知IDが必要です'}, status=400)
        
        NotificationService.mark_as_read(request.user, notification_id)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def mark_all_notifications_read(request):
    """すべての通知を既読にする"""
    try:
        NotificationService.mark_all_as_read(request.user)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

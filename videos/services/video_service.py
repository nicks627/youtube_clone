# Video Service - Handles video-related business logic

from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from ..models import Video, Like, WatchHistory, WatchLater


class VideoService:
    """Service class for video-related operations"""
    
    @staticmethod
    def get_featured_videos(page=1, per_page=20):
        """Get featured videos with pagination and performance optimization"""
        cache_key = f'featured_videos_page_{page}'
        videos = cache.get(cache_key)
        
        if not videos:
            video_list = Video.objects.select_related(
                'uploaded_by', 'uploaded_by__channel'
            ).prefetch_related(
                'likes', 'genres'
            ).filter(
                uploaded_by__is_active=True
            ).order_by('-views', '-uploaded_at')
            
            paginator = Paginator(video_list, per_page)
            videos = paginator.get_page(page)
            
            # Cache for 10 minutes
            cache.set(cache_key, videos, 600)
        
        return videos
    
    @staticmethod
    def get_videos_by_genre(genre_slug, page=1, per_page=20):
        """Get videos filtered by genre"""
        cache_key = f'videos_genre_{genre_slug}_page_{page}'
        videos = cache.get(cache_key)
        
        if not videos:
            video_list = Video.objects.select_related(
                'uploaded_by', 'uploaded_by__channel'
            ).prefetch_related(
                'likes', 'genres'
            ).filter(
                genres__slug=genre_slug,
                uploaded_by__is_active=True
            ).order_by('-views', '-uploaded_at')
            
            paginator = Paginator(video_list, per_page)
            videos = paginator.get_page(page)
            
            # Cache for 15 minutes
            cache.set(cache_key, videos, 900)
        
        return videos
    
    @staticmethod
    def search_videos(query, page=1, per_page=20):
        """Search videos by title and description"""
        if not query:
            return VideoService.get_featured_videos(page, per_page)
        
        video_list = Video.objects.select_related(
            'uploaded_by', 'uploaded_by__channel'
        ).prefetch_related(
            'likes', 'genres'
        ).filter(
            Q(title__icontains=query) | Q(description__icontains=query),
            uploaded_by__is_active=True
        ).order_by('-views', '-uploaded_at')
        
        paginator = Paginator(video_list, per_page)
        return paginator.get_page(page)
    
    @staticmethod
    def get_trending_videos(page=1, per_page=20):
        """Get trending videos based on recent views and likes"""
        cache_key = f'trending_videos_page_{page}'
        videos = cache.get(cache_key)
        
        if not videos:
            # Videos from last 7 days with high engagement
            last_week = timezone.now() - timedelta(days=7)
            
            video_list = Video.objects.select_related(
                'uploaded_by', 'uploaded_by__channel'
            ).prefetch_related(
                'likes'
            ).filter(
                uploaded_at__gte=last_week,
                uploaded_by__is_active=True
            ).annotate(
                like_count=Count('likes'),
                engagement_score=Count('likes') + Count('views') / 10
            ).order_by('-engagement_score', '-uploaded_at')
            
            paginator = Paginator(video_list, per_page)
            videos = paginator.get_page(page)
            
            # Cache for 30 minutes
            cache.set(cache_key, videos, 1800)
        
        return videos
    
    @staticmethod
    def get_user_videos(user, page=1, per_page=20):
        """Get videos uploaded by a specific user"""
        video_list = Video.objects.select_related(
            'uploaded_by', 'uploaded_by__channel'
        ).prefetch_related(
            'likes', 'genres'
        ).filter(
            uploaded_by=user
        ).order_by('-uploaded_at')
        
        paginator = Paginator(video_list, per_page)
        return paginator.get_page(page)
    
    @staticmethod
    def get_liked_videos(user, page=1, per_page=20):
        """Get videos liked by a user"""
        liked_video_ids = Like.objects.filter(user=user).values_list('video_id', flat=True)
        
        video_list = Video.objects.select_related(
            'uploaded_by', 'uploaded_by__channel'
        ).prefetch_related(
            'likes', 'genres'
        ).filter(
            id__in=liked_video_ids,
            uploaded_by__is_active=True
        ).order_by('-likes__created_at')
        
        paginator = Paginator(video_list, per_page)
        return paginator.get_page(page)
    
    @staticmethod
    def get_watch_history(user, page=1, per_page=20):
        """Get user's watch history"""
        history_list = WatchHistory.objects.select_related(
            'video', 'video__uploaded_by', 'video__uploaded_by__channel'
        ).prefetch_related(
            'video__likes', 'video__genres'
        ).filter(
            user=user,
            video__uploaded_by__is_active=True
        ).order_by('-watched_at')
        
        paginator = Paginator(history_list, per_page)
        return paginator.get_page(page)
    
    @staticmethod
    def get_watch_later_videos(user, page=1, per_page=20):
        """Get user's watch later videos"""
        watch_later_video_ids = WatchLater.objects.filter(user=user).values_list('video_id', flat=True)
        
        video_list = Video.objects.select_related(
            'uploaded_by', 'uploaded_by__channel'
        ).prefetch_related(
            'likes', 'genres'
        ).filter(
            id__in=watch_later_video_ids,
            uploaded_by__is_active=True
        ).order_by('-watchlater__created_at')
        
        paginator = Paginator(video_list, per_page)
        return paginator.get_page(page)
    
    @staticmethod
    def increment_view_count(video):
        """Increment view count for a video"""
        video.views += 1
        video.save(update_fields=['views'])
        
        # Clear related cache
        cache.delete(f'featured_videos_page_1')
        for genre in video.genres.all():
            cache.delete(f'videos_genre_{genre.slug}_page_1')
    
    @staticmethod
    def toggle_like(user, video):
        """Toggle like status for a video"""
        like, created = Like.objects.get_or_create(user=user, video=video)
        
        if not created:
            like.delete()
            return False  # Unliked
        
        return True  # Liked
    
    @staticmethod
    def toggle_watch_later(user, video):
        """Toggle watch later status for a video"""
        watch_later, created = WatchLater.objects.get_or_create(user=user, video=video)
        
        if not created:
            watch_later.delete()
            return False  # Removed from watch later
        
        return True  # Added to watch later
    
    @staticmethod
    def add_to_history(user, video):
        """Add video to user's watch history"""
        WatchHistory.objects.update_or_create(
            user=user,
            video=video,
            defaults={'watched_at': timezone.now()}
        )
    
    @staticmethod
    def get_video_with_details(video_id):
        """Get video with all related data for detail view"""
        try:
            return Video.objects.select_related(
                'uploaded_by', 'uploaded_by__channel'
            ).prefetch_related(
                'likes', 'genres', 'comments__user', 'comments__user__channel'
            ).get(id=video_id)
        except Video.DoesNotExist:
            return None
    
    @staticmethod
    def get_related_videos(video, limit=10):
        """Get videos related to the current video"""
        cache_key = f'related_videos_{video.id}'
        related_videos = cache.get(cache_key)
        
        if not related_videos:
            # Get videos from same genres or same channel
            related_videos = Video.objects.select_related(
                'uploaded_by', 'uploaded_by__channel'
            ).prefetch_related(
                'likes', 'genres'
            ).filter(
                Q(genres__in=video.genres.all()) | Q(uploaded_by=video.uploaded_by),
                uploaded_by__is_active=True
            ).exclude(
                id=video.id
            ).distinct().order_by('-views')[:limit]
            
            # Cache for 1 hour
            cache.set(cache_key, related_videos, 3600)
        
        return related_videos
    
    @staticmethod
    def get_shorts_videos(page=1, per_page=20):
        """Get short-form videos (assuming duration <= 60 seconds)"""
        cache_key = f'shorts_videos_page_{page}'
        videos = cache.get(cache_key)
        
        if not videos:
            video_list = Video.objects.select_related(
                'uploaded_by', 'uploaded_by__channel'
            ).prefetch_related(
                'likes', 'genres'
            ).filter(
                duration__lte=60,  # Short videos (60 seconds or less)
                uploaded_by__is_active=True
            ).order_by('-views', '-uploaded_at')
            
            paginator = Paginator(video_list, per_page)
            videos = paginator.get_page(page)
            
            # Cache for 15 minutes
            cache.set(cache_key, videos, 900)
        
        return videos
    
    @staticmethod
    def clear_video_caches():
        """Clear all video-related caches"""
        cache_patterns = [
            'featured_videos_page_*',
            'videos_genre_*',
            'trending_videos_page_*',
            'shorts_videos_page_*',
            'related_videos_*'
        ]
        
        # Note: This is a simplified cache clearing
        # In production, you might want to use cache versioning
        for i in range(1, 11):  # Clear first 10 pages
            cache.delete(f'featured_videos_page_{i}')
            cache.delete(f'trending_videos_page_{i}')
            cache.delete(f'shorts_videos_page_{i}')
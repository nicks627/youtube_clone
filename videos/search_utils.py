# Search utilities and enhancements
from django.db.models import Q, Count, F, Value, IntegerField, Case, When
from django.db.models.functions import Lower
from django.utils import timezone
from datetime import timedelta
import json

class SearchEnhancer:
    """Enhanced search functionality for videos"""
    
    SORT_OPTIONS = {
        'relevance': 'Relevance',
        'upload_date': 'Upload date',
        'view_count': 'View count',
        'rating': 'Rating',
    }
    
    UPLOAD_DATE_FILTERS = {
        'hour': ('Last hour', timedelta(hours=1)),
        'today': ('Today', timedelta(days=1)),
        'week': ('This week', timedelta(weeks=1)),
        'month': ('This month', timedelta(days=30)),
        'year': ('This year', timedelta(days=365)),
    }
    
    DURATION_FILTERS = {
        'short': ('Short (< 4 minutes)', 0, 240),
        'medium': ('Medium (4-20 minutes)', 240, 1200),
        'long': ('Long (> 20 minutes)', 1200, None),
    }
    
    @staticmethod
    def search_videos(query, filters=None):
        """
        Enhanced search with filters and better relevance scoring
        """
        from .models import Video
        
        if not query:
            return Video.objects.none()
        
        # Base queryset
        queryset = Video.objects.select_related('uploaded_by__channel').prefetch_related(
            'genres', 'likes'
        ).filter(uploaded_by__is_active=True)
        
        # Apply text search with relevance scoring
        search_conditions = Q()
        
        # Exact match in title (highest priority)
        search_conditions |= Q(title__iexact=query)
        
        # Word match in title
        for word in query.split():
            if len(word) > 2:  # Skip short words
                search_conditions |= Q(title__icontains=word)
        
        # Match in description and username (lower priority)
        search_conditions |= Q(description__icontains=query)
        search_conditions |= Q(uploaded_by__username__icontains=query)
        search_conditions |= Q(uploaded_by__channel__name__icontains=query)
        
        # Match in genres
        search_conditions |= Q(genres__name__icontains=query)
        
        queryset = queryset.filter(search_conditions).distinct()
        
        # Apply filters if provided
        if filters:
            queryset = SearchEnhancer._apply_filters(queryset, filters)
        
        # Apply sorting
        sort_by = filters.get('sort_by', 'relevance') if filters else 'relevance'
        queryset = SearchEnhancer._apply_sorting(queryset, sort_by, query)
        
        return queryset
    
    @staticmethod
    def _apply_filters(queryset, filters):
        """Apply various filters to the queryset"""
        
        # Upload date filter
        upload_date = filters.get('upload_date')
        if upload_date and upload_date in SearchEnhancer.UPLOAD_DATE_FILTERS:
            _, timedelta_obj = SearchEnhancer.UPLOAD_DATE_FILTERS[upload_date]
            date_threshold = timezone.now() - timedelta_obj
            queryset = queryset.filter(uploaded_at__gte=date_threshold)
        
        # Duration filter
        duration = filters.get('duration')
        if duration and duration in SearchEnhancer.DURATION_FILTERS:
            _, min_seconds, max_seconds = SearchEnhancer.DURATION_FILTERS[duration]
            if min_seconds is not None:
                queryset = queryset.filter(duration__gte=min_seconds)
            if max_seconds is not None:
                queryset = queryset.filter(duration__lt=max_seconds)
        
        # Genre filter
        genre = filters.get('genre')
        if genre:
            queryset = queryset.filter(genres__slug=genre)
        
        # Type filter (regular videos vs shorts)
        video_type = filters.get('type')
        if video_type == 'shorts':
            queryset = queryset.filter(is_shorts=True)
        elif video_type == 'regular':
            queryset = queryset.filter(is_shorts=False)
        
        return queryset
    
    @staticmethod
    def _apply_sorting(queryset, sort_by, query=None):
        """Apply sorting to the queryset"""
        
        if sort_by == 'upload_date':
            return queryset.order_by('-uploaded_at')
        elif sort_by == 'view_count':
            return queryset.order_by('-views')
        elif sort_by == 'rating':
            # Sort by like ratio
            return queryset.annotate(
                like_count=Count('likes')
            ).order_by('-like_count', '-uploaded_at')
        else:  # relevance
            if query:
                # Simple relevance scoring based on title match
                return queryset.annotate(
                    exact_match=Case(
                        When(title__iexact=query, then=Value(3)),
                        default=Value(0),
                        output_field=IntegerField()
                    ),
                    title_match=Case(
                        When(title__icontains=query, then=Value(2)),
                        default=Value(0),
                        output_field=IntegerField()
                    ),
                    relevance_score=F('exact_match') + F('title_match')
                ).order_by('-relevance_score', '-views', '-uploaded_at')
            else:
                return queryset.order_by('-views', '-uploaded_at')
    
    @staticmethod
    def get_search_suggestions(query, limit=10):
        """Get search suggestions based on partial query"""
        from .models import Video
        
        if not query or len(query) < 2:
            return []
        
        # Get video titles that match the query
        suggestions = Video.objects.filter(
            Q(title__istartswith=query) |
            Q(title__icontains=' ' + query)
        ).values_list('title', flat=True).distinct()[:limit]
        
        # Convert to list and sort by relevance
        suggestions_list = list(suggestions)
        
        # Sort with exact prefix matches first
        suggestions_list.sort(key=lambda x: (
            not x.lower().startswith(query.lower()),
            len(x),
            x.lower()
        ))
        
        return suggestions_list[:limit]
    
    @staticmethod
    def get_trending_searches(limit=10):
        """Get trending search terms"""
        from .models import Video
        
        # Get most viewed videos from the last week
        one_week_ago = timezone.now() - timedelta(days=7)
        trending_videos = Video.objects.filter(
            uploaded_at__gte=one_week_ago
        ).order_by('-views')[:20]
        
        # Extract common words from titles (simple approach)
        word_count = {}
        for video in trending_videos:
            words = video.title.lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    word_count[word] = word_count.get(word, 0) + 1
        
        # Sort by frequency and return top words
        trending_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in trending_words[:limit]]


class SearchHistory:
    """Manage user search history"""
    
    @staticmethod
    def add_search(request, query):
        """Add a search to user's history"""
        if not request.user.is_authenticated or not query:
            return
        
        # Store in session
        history = request.session.get('search_history', [])
        
        # Remove if already exists
        if query in history:
            history.remove(query)
        
        # Add to beginning
        history.insert(0, query)
        
        # Keep only last 20 searches
        history = history[:20]
        
        request.session['search_history'] = history
    
    @staticmethod
    def get_history(request, limit=10):
        """Get user's search history"""
        if not request.user.is_authenticated:
            return []
        
        history = request.session.get('search_history', [])
        return history[:limit]
    
    @staticmethod
    def clear_history(request):
        """Clear user's search history"""
        if not request.user.is_authenticated:
            return
        
        if 'search_history' in request.session:
            del request.session['search_history']
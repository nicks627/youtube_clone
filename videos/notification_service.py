from django.contrib.auth.models import User
from django.utils import timezone
from django.core.cache import cache
import json

class NotificationService:
    """通知管理サービス"""
    
    @staticmethod
    def create_notification(user, notification_type, title, message, related_object_id=None, action_url=None):
        """
        新しい通知を作成
        
        Args:
            user: 通知を受け取るユーザー
            notification_type: 通知タイプ ('subscription', 'like', 'comment', 'system')
            title: 通知タイトル
            message: 通知メッセージ
            related_object_id: 関連オブジェクトのID（動画ID、コメントIDなど）
            action_url: アクションURL
        """
        notification = {
            'id': f"{user.id}_{int(timezone.now().timestamp() * 1000)}",
            'type': notification_type,
            'title': title,
            'message': message,
            'created_at': timezone.now().isoformat(),
            'unread': True,
            'related_object_id': related_object_id,
            'action_url': action_url
        }
        
        # キャッシュに保存（ユーザーごとに通知リストを管理）
        cache_key = f"notifications_{user.id}"
        notifications = cache.get(cache_key, [])
        notifications.insert(0, notification)  # 新しい通知を先頭に
        
        # 最大50件まで保持
        notifications = notifications[:50]
        
        # 24時間キャッシュ
        cache.set(cache_key, notifications, 86400)
        
        return notification
    
    @staticmethod
    def get_user_notifications(user, limit=20):
        """
        ユーザーの通知一覧を取得
        
        Args:
            user: ユーザー
            limit: 取得件数
            
        Returns:
            list: 通知リスト
        """
        cache_key = f"notifications_{user.id}"
        notifications = cache.get(cache_key, [])
        return notifications[:limit]
    
    @staticmethod
    def mark_as_read(user, notification_id):
        """
        通知を既読にする
        
        Args:
            user: ユーザー
            notification_id: 通知ID
        """
        cache_key = f"notifications_{user.id}"
        notifications = cache.get(cache_key, [])
        
        for notification in notifications:
            if notification['id'] == notification_id:
                notification['unread'] = False
                break
        
        cache.set(cache_key, notifications, 86400)
    
    @staticmethod
    def mark_all_as_read(user):
        """
        すべての通知を既読にする
        
        Args:
            user: ユーザー
        """
        cache_key = f"notifications_{user.id}"
        notifications = cache.get(cache_key, [])
        
        for notification in notifications:
            notification['unread'] = False
        
        cache.set(cache_key, notifications, 86400)
    
    @staticmethod
    def get_unread_count(user):
        """
        未読通知数を取得
        
        Args:
            user: ユーザー
            
        Returns:
            int: 未読通知数
        """
        notifications = NotificationService.get_user_notifications(user)
        return sum(1 for n in notifications if n.get('unread', False))
    
    @staticmethod
    def notify_new_video(video):
        """
        新しい動画アップロード時の通知
        
        Args:
            video: Video オブジェクト
        """
        from .models import Subscription
        
        # チャンネル登録者に通知
        subscribers = Subscription.objects.filter(
            channel__user=video.uploaded_by
        ).select_related('subscriber')
        
        for subscription in subscribers:
            NotificationService.create_notification(
                user=subscription.subscriber,
                notification_type='subscription',
                title='新しい動画',
                message=f'{video.uploaded_by.username}が新しい動画「{video.title}」をアップロードしました',
                related_object_id=video.id,
                action_url=f'/video/{video.id}/'
            )
    
    @staticmethod
    def notify_new_comment(comment):
        """
        新しいコメント時の通知
        
        Args:
            comment: Comment オブジェクト
        """
        video_owner = comment.video.uploaded_by
        
        # 動画投稿者に通知（自分のコメントは除く）
        if comment.user != video_owner:
            NotificationService.create_notification(
                user=video_owner,
                notification_type='comment',
                title='新しいコメント',
                message=f'{comment.user.username}があなたの動画「{comment.video.title}」にコメントしました',
                related_object_id=comment.video.id,
                action_url=f'/video/{comment.video.id}/'
            )
    
    @staticmethod
    def notify_new_like(video_like):
        """
        新しい高評価時の通知
        
        Args:
            video_like: VideoLike オブジェクト
        """
        if video_like.like_type == 1:  # 高評価の場合のみ
            video_owner = video_like.video.uploaded_by
            
            # 動画投稿者に通知（自分の評価は除く）
            if video_like.user != video_owner:
                NotificationService.create_notification(
                    user=video_owner,
                    notification_type='like',
                    title='高評価',
                    message=f'{video_like.user.username}があなたの動画「{video_like.video.title}」に高評価しました',
                    related_object_id=video_like.video.id,
                    action_url=f'/video/{video_like.video.id}/'
                )
    
    @staticmethod
    def notify_new_subscription(subscription):
        """
        新しいチャンネル登録時の通知
        
        Args:
            subscription: Subscription オブジェクト
        """
        channel_owner = subscription.channel.user
        
        NotificationService.create_notification(
            user=channel_owner,
            notification_type='subscription',
            title='新しい登録者',
            message=f'{subscription.subscriber.username}があなたのチャンネルに登録しました',
            related_object_id=subscription.channel.id,
            action_url=f'/channel/{channel_owner.username}/'
        )
from django.db import models
from django.contrib.auth.models import User
import os

class Video(models.Model):
    GENRE_CHOICES = [
        ('trending', '急上昇'),
        ('music', '音楽'),
        ('gaming', 'ゲーム'),
        ('news', 'ニュース'),
        ('sports', 'スポーツ'),
        ('entertainment', 'エンターテイメント'),
        ('education', '教育'),
        ('technology', 'テクノロジー'),
        ('lifestyle', 'ライフスタイル'),
        ('comedy', 'コメディ'),
        ('other', 'その他'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    video_file = models.FileField(upload_to='videos/')
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    views = models.PositiveIntegerField(default=0)
    genre = models.CharField(max_length=20, choices=GENRE_CHOICES, default='other')
    is_paid = models.BooleanField(default=False, help_text="有料コンテンツかどうか")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="価格（円）")
    duration = models.PositiveIntegerField(null=True, blank=True, help_text="動画の長さ（秒）")
    is_shorts = models.BooleanField(default=False, help_text="ショート動画かどうか（60秒以下）")
    
    def get_like_count(self):
        return self.likes.filter(like_type=1).count()
    
    def get_dislike_count(self):
        return self.likes.filter(like_type=-1).count()
    
    def get_comment_count(self):
        return self.comments.filter(parent=None).count()  # Only top-level comments
    
    def get_duration_display(self):
        """動画の長さを MM:SS または HH:MM:SS フォーマットで返す"""
        if not self.duration:
            return "0:00"
        
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    def save(self, *args, **kwargs):
        """保存時に動画の長さに基づいてショート動画かどうかを自動判定"""
        if self.duration and self.duration <= 60:
            self.is_shorts = True
        else:
            self.is_shorts = False
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-uploaded_at']

class Channel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='channel')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    bio = models.TextField(blank=True, help_text="チャンネルの紹介文")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    banner = models.ImageField(upload_to='banners/', blank=True, null=True)
    subscriber_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    website = models.URLField(blank=True, help_text="ウェブサイトURL")
    twitter_handle = models.CharField(max_length=50, blank=True, help_text="@なしのTwitterハンドル")
    
    def __str__(self):
        return self.name
    
    def get_subscriber_count_display(self):
        if self.subscriber_count >= 1000000:
            return f"{self.subscriber_count / 1000000:.1f}M"
        elif self.subscriber_count >= 1000:
            return f"{self.subscriber_count / 1000:.1f}K"
        return str(self.subscriber_count)

class SubscriptionFolder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscription_folders')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#ff0000')  # Hex color
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = ['user', 'name']
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"

class Subscription(models.Model):
    subscriber = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='subscribers')
    folder = models.ForeignKey(SubscriptionFolder, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    subscribed_at = models.DateTimeField(auto_now_add=True)
    notifications_enabled = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['subscriber', 'channel']
        ordering = ['-subscribed_at']
    
    def __str__(self):
        return f"{self.subscriber.username} subscribed to {self.channel.name}"

# Signal to create channel when user is created
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    default_playback_speed = models.FloatField(default=1.0, choices=[
        (0.25, '0.25x'),
        (0.5, '0.5x'),
        (0.75, '0.75x'),
        (1.0, '標準'),
        (1.25, '1.25x'),
        (1.5, '1.5x'),
        (1.75, '1.75x'),
        (2.0, '2x'),
        (2.5, '2.5x'),
        (3.0, '3x'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}の設定"

@receiver(post_save, sender=User)
def create_user_channel(sender, instance, created, **kwargs):
    if created:
        Channel.objects.create(
            user=instance,
            name=instance.username,
            description=f"{instance.username}のチャンネル"
        )

class WatchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watch_history')
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    watched_at = models.DateTimeField(auto_now_add=True)
    watch_progress = models.FloatField(default=0.0)  # Progress in seconds
    
    class Meta:
        unique_together = ['user', 'video']
        ordering = ['-watched_at']
    
    def __str__(self):
        return f"{self.user.username} watched {self.video.title}"

class WatchLater(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watch_later')
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'video']
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.video.title}"

class Comment(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} on {self.video.title}: {self.content[:50]}..."
    
    @property
    def is_reply(self):
        return self.parent is not None

class VideoLike(models.Model):
    LIKE_CHOICES = [
        (1, 'Like'),
        (-1, 'Dislike'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='likes')
    like_type = models.IntegerField(choices=LIKE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'video']
        ordering = ['-created_at']
    
    def __str__(self):
        like_text = "liked" if self.like_type == 1 else "disliked"
        return f"{self.user.username} {like_text} {self.video.title}"

@receiver(post_save, sender=User)
def create_user_settings(sender, instance, created, **kwargs):
    if created:
        UserSettings.objects.create(user=instance)

# Payment and Content Models
class PaymentSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='payment_settings')
    link_api_key = models.CharField(max_length=255, blank=True, help_text="Link決済のAPIキー")
    link_secret_key = models.CharField(max_length=255, blank=True, help_text="Link決済のシークレットキー")
    is_payments_enabled = models.BooleanField(default=False, help_text="決済機能を有効にする")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}の決済設定"

class PaidContent(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('video', '動画'),
        ('channel_subscription', 'チャンネル購読'),
        ('live_stream', 'ライブ配信'),
        ('exclusive_content', '限定コンテンツ'),
    ]
    
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name='paid_content', null=True, blank=True)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='paid_contents')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='video')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="価格（円）")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - ¥{self.price}"

class Purchase(models.Model):
    PURCHASE_STATUS_CHOICES = [
        ('pending', '支払い待ち'),
        ('completed', '支払い完了'),
        ('failed', '支払い失敗'),
        ('refunded', '返金済み'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    paid_content = models.ForeignKey(PaidContent, on_delete=models.CASCADE, related_name='purchases')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PURCHASE_STATUS_CHOICES, default='pending')
    link_transaction_id = models.CharField(max_length=255, blank=True, help_text="Link決済のトランザクションID")
    purchased_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'paid_content']
        ordering = ['-purchased_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.paid_content.title} - {self.status}"

class Donation(models.Model):
    DONATION_STATUS_CHOICES = [
        ('pending', '支払い待ち'),
        ('completed', '支払い完了'),
        ('failed', '支払い失敗'),
    ]
    
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations_received')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='donations', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(blank=True, max_length=200)
    status = models.CharField(max_length=20, choices=DONATION_STATUS_CHOICES, default='pending')
    link_transaction_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username} ¥{self.amount}"

@receiver(post_save, sender=User)
def create_payment_settings(sender, instance, created, **kwargs):
    if created:
        PaymentSettings.objects.create(user=instance)

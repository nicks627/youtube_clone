from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Video, Channel, Subscription, UserSettings, Comment, VideoLike, WatchHistory, WatchLater
import tempfile
import os

class VideoModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.video = Video.objects.create(
            title='Test Video',
            description='Test Description',
            uploaded_by=self.user,
            genre='music'
        )

    def test_video_creation(self):
        self.assertEqual(self.video.title, 'Test Video')
        self.assertEqual(self.video.uploaded_by, self.user)
        self.assertEqual(self.video.views, 0)
        self.assertEqual(self.video.genre, 'music')

    def test_video_like_count(self):
        # Test initial like count
        self.assertEqual(self.video.get_like_count(), 0)
        self.assertEqual(self.video.get_dislike_count(), 0)
        
        # Add likes
        VideoLike.objects.create(user=self.user, video=self.video, like_type=1)
        self.assertEqual(self.video.get_like_count(), 1)
        self.assertEqual(self.video.get_dislike_count(), 0)

    def test_video_comment_count(self):
        # Test initial comment count
        self.assertEqual(self.video.get_comment_count(), 0)
        
        # Add comment
        Comment.objects.create(user=self.user, video=self.video, content='Test comment')
        self.assertEqual(self.video.get_comment_count(), 1)

class UserSettingsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_user_settings_creation(self):
        # UserSettings should be created automatically when user is created
        self.assertTrue(hasattr(self.user, 'settings'))
        self.assertEqual(self.user.settings.default_playback_speed, 1.0)

class CommentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.video = Video.objects.create(
            title='Test Video',
            uploaded_by=self.user
        )

    def test_comment_creation(self):
        comment = Comment.objects.create(
            user=self.user,
            video=self.video,
            content='This is a test comment'
        )
        self.assertEqual(comment.content, 'This is a test comment')
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.video, self.video)
        self.assertIsNone(comment.parent)
        self.assertFalse(comment.is_reply)

    def test_comment_reply(self):
        parent_comment = Comment.objects.create(
            user=self.user,
            video=self.video,
            content='Parent comment'
        )
        reply = Comment.objects.create(
            user=self.user,
            video=self.video,
            content='Reply comment',
            parent=parent_comment
        )
        self.assertTrue(reply.is_reply)
        self.assertEqual(reply.parent, parent_comment)

class VideoViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.video = Video.objects.create(
            title='Test Video',
            description='Test Description',
            uploaded_by=self.user
        )

    def test_video_list_view(self):
        response = self.client.get(reverse('video_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Video')

    def test_video_detail_view_unauthenticated(self):
        response = self.client.get(reverse('video_detail', args=[self.video.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Video')

    def test_video_detail_view_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('video_detail', args=[self.video.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Video')
        
        # Check if watch history was created
        self.assertTrue(WatchHistory.objects.filter(user=self.user, video=self.video).exists())

    def test_search_view(self):
        response = self.client.get(reverse('search_videos'), {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Video')

    def test_search_view_no_query(self):
        response = self.client.get(reverse('search_videos'))
        self.assertEqual(response.status_code, 302)  # Redirects to video_list

    def test_explore_view(self):
        response = self.client.get(reverse('explore'))
        self.assertEqual(response.status_code, 200)

    def test_trending_view(self):
        response = self.client.get(reverse('trending'))
        self.assertEqual(response.status_code, 200)

    def test_shorts_view(self):
        response = self.client.get(reverse('shorts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '近日公開予定')

class AuthenticatedViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.video = Video.objects.create(
            title='Test Video',
            uploaded_by=self.user
        )

    def test_history_view_requires_login(self):
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_history_view_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 200)

    def test_watch_later_view_requires_login(self):
        response = self.client.get(reverse('watch_later'))
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_watch_later_view_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('watch_later'))
        self.assertEqual(response.status_code, 200)

    def test_account_settings_view_requires_login(self):
        response = self.client.get(reverse('account_settings'))
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_account_settings_view_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('account_settings'))
        self.assertEqual(response.status_code, 200)

class APIViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass123')
        self.video = Video.objects.create(
            title='Test Video',
            uploaded_by=self.other_user
        )
        self.channel = Channel.objects.get(user=self.other_user)

    def test_toggle_watch_later_requires_login(self):
        response = self.client.post(reverse('toggle_watch_later'), 
                                   data={'video_id': self.video.id},
                                   content_type='application/json')
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_toggle_watch_later_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('toggle_watch_later'), 
                                   data='{"video_id": %d}' % self.video.id,
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['in_watch_later'])
        self.assertIn('message', data)

    def test_add_comment_requires_login(self):
        response = self.client.post(reverse('add_comment'),
                                   data={'video_id': self.video.id, 'content': 'Test comment'},
                                   content_type='application/json')
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_add_comment_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('add_comment'),
                                   data='{"video_id": %d, "content": "Test comment"}' % self.video.id,
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['content'], 'Test comment')
        self.assertEqual(data['username'], 'testuser')

    def test_toggle_video_like_requires_login(self):
        response = self.client.post(reverse('toggle_video_like'),
                                   data={'video_id': self.video.id, 'like_type': 1},
                                   content_type='application/json')
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_toggle_video_like_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('toggle_video_like'),
                                   data='{"video_id": %d, "like_type": 1}' % self.video.id,
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['liked'])
        self.assertEqual(data['like_type'], 1)
        self.assertEqual(data['like_count'], 1)

    def test_toggle_subscription_requires_login(self):
        response = self.client.post(reverse('toggle_subscription'),
                                   data={'channel_id': self.channel.id},
                                   content_type='application/json')
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_toggle_subscription_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('toggle_subscription'),
                                   data='{"channel_id": %d}' % self.channel.id,
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['subscribed'])

class SignupTest(TestCase):
    def test_signup_view_get(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')

    def test_signup_view_post_valid(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'password1': 'testpass123456',
            'password2': 'testpass123456'
        })
        self.assertEqual(response.status_code, 302)  # Redirects after successful signup
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_signup_view_post_invalid(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'password1': 'testpass123456',
            'password2': 'different_password'
        })
        self.assertEqual(response.status_code, 200)  # Stays on form with errors
        self.assertFalse(User.objects.filter(username='newuser').exists())

class ChannelModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_channel_creation_on_user_creation(self):
        # Channel should be created automatically when user is created
        self.assertTrue(hasattr(self.user, 'channel'))
        self.assertEqual(self.user.channel.name, 'testuser')

    def test_channel_subscriber_count_display(self):
        channel = self.user.channel
        
        # Test subscriber count display formatting
        channel.subscriber_count = 500
        self.assertEqual(channel.get_subscriber_count_display(), '500')
        
        channel.subscriber_count = 1500
        self.assertEqual(channel.get_subscriber_count_display(), '1.5K')
        
        channel.subscriber_count = 1500000
        self.assertEqual(channel.get_subscriber_count_display(), '1.5M')

class SubscriptionTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
        self.channel1 = self.user1.channel
        self.channel2 = self.user2.channel

    def test_subscription_creation(self):
        subscription = Subscription.objects.create(
            subscriber=self.user1,
            channel=self.channel2
        )
        self.assertEqual(subscription.subscriber, self.user1)
        self.assertEqual(subscription.channel, self.channel2)
        self.assertTrue(subscription.notifications_enabled)

class GenreFilterTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.music_video = Video.objects.create(
            title='Music Video',
            uploaded_by=self.user,
            genre='music'
        )
        self.gaming_video = Video.objects.create(
            title='Gaming Video',
            uploaded_by=self.user,
            genre='gaming'
        )

    def test_genre_filter_view(self):
        response = self.client.get(reverse('video_list_by_genre', args=['music']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Music Video')
        self.assertNotContains(response, 'Gaming Video')

    def test_invalid_genre_redirects(self):
        response = self.client.get(reverse('video_list_by_genre', args=['invalid_genre']))
        self.assertEqual(response.status_code, 302)  # Redirects to video_list

class UserContentViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass123')
        self.video = Video.objects.create(
            title='Test Video',
            uploaded_by=self.user,
            genre='music'
        )
        self.other_video = Video.objects.create(
            title='Other Video',
            uploaded_by=self.other_user,
            genre='gaming'
        )

    def test_subscriptions_list_view_requires_login(self):
        response = self.client.get(reverse('subscriptions'))
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_subscriptions_list_view_authenticated_no_subscriptions(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('subscriptions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '登録チャンネル')

    def test_your_videos_view_requires_login(self):
        response = self.client.get(reverse('your_videos'))
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_your_videos_view_authenticated_no_videos(self):
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(reverse('your_videos'))
        self.assertEqual(response.status_code, 200)
        # Check for the empty state content
        self.assertContains(response, 'あなたの動画')

    def test_your_videos_view_authenticated_with_videos(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('your_videos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Video')
        self.assertNotContains(response, 'Other Video')

    def test_liked_videos_view_requires_login(self):
        response = self.client.get(reverse('liked_videos'))
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_liked_videos_view_authenticated_no_likes(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('liked_videos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '高評価した動画')

    def test_liked_videos_view_authenticated_with_likes(self):
        self.client.login(username='testuser', password='testpass123')
        # Like the other user's video
        VideoLike.objects.create(user=self.user, video=self.other_video, like_type=1)
        response = self.client.get(reverse('liked_videos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Other Video')
        self.assertNotContains(response, 'Test Video')
#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings

# Django settings configuration
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'youtube_clone.settings')
sys.path.append('/home/tai/youtube_clone')

django.setup()

from django.contrib.auth.models import User
from videos.models import Video, Channel
from django.core.files.base import ContentFile
import base64

def create_sample_mp4():
    """Create a minimal valid MP4 file"""
    # Minimal MP4 header (ftyp box)
    ftyp = b'\x00\x00\x00\x20\x66\x74\x79\x70\x6d\x70\x34\x31\x00\x00\x00\x00\x6d\x70\x34\x31\x69\x73\x6f\x6d\x68\x6c\x73\x66\x00\x00\x00\x00'
    # moov box (minimal)
    moov = b'\x00\x00\x00\x08\x6d\x6f\x6f\x76'
    return ftyp + moov

def create_sample_data():
    print("サンプルデータを作成中...")
    
    # Create superuser if not exists
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("管理者ユーザー 'admin' を作成しました（パスワード: admin123）")
    
    # Create test user
    test_user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
        }
    )
    if created:
        test_user.set_password('test123')
        test_user.save()
        print("テストユーザー 'testuser' を作成しました（パスワード: test123）")
    
    # Create sample videos
    sample_videos = [
        {
            'title': 'サンプル動画1 - テスト動画',
            'description': 'これはテスト用のサンプル動画です。動画プレーヤーの機能をテストするために作成されました。',
            'user': admin_user
        },
        {
            'title': 'サンプル動画2 - デモンストレーション',
            'description': 'YouTubeクローンアプリケーションのデモンストレーション動画です。倍速再生機能なども試すことができます。',
            'user': test_user
        },
        {
            'title': 'サンプル動画3 - 機能テスト',
            'description': 'エラーハンドリングや各種機能のテストのためのサンプル動画です。',
            'user': admin_user
        }
    ]
    
    for i, video_data in enumerate(sample_videos, 1):
        video, created = Video.objects.get_or_create(
            title=video_data['title'],
            defaults={
                'description': video_data['description'],
                'uploaded_by': video_data['user']
            }
        )
        
        if created:
            # Create minimal MP4 file
            mp4_content = create_sample_mp4()
            video.video_file.save(
                f'sample_video_{i}.mp4',
                ContentFile(mp4_content),
                save=True
            )
            print(f"サンプル動画 '{video_data['title']}' を作成しました")
    
    print("\nサンプルデータの作成が完了しました！")
    # Create channels for existing users if they don't exist
    for user in User.objects.all():
        channel, created = Channel.objects.get_or_create(
            user=user,
            defaults={
                'name': user.username,
                'description': f'{user.username}のチャンネル'
            }
        )
        if created:
            print(f"{user.username}のチャンネルを作成しました")
    
    print("管理者でログイン: admin / admin123")
    print("テストユーザーでログイン: testuser / test123")
    print("\n開発サーバーを起動するには:")
    print("python manage.py runserver")
    print("\nチャンネル登録機能をテストするには:")
    print("1. 管理者でログインしてtestuserの動画を見る")
    print("2. チャンネル登録ボタンをクリック")
    print("3. /subscriptions/ で登録チャンネルを管理")

if __name__ == '__main__':
    create_sample_data()
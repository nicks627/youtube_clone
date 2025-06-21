from django import forms
from django.core.exceptions import ValidationError
from .models import Video
from .utils import get_video_duration
import os

class VideoUploadForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['title', 'description', 'video_file', 'thumbnail', 'genre', 'is_paid', 'price', 'is_shorts']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'タイトルを入力'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': '説明を入力'}),
            'video_file': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/mp4'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'genre': forms.Select(attrs={'class': 'form-control'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_is_paid'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '価格（円）', 'min': '100', 'step': '10'}),
            'is_shorts': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_is_shorts'}),
        }
    
    def clean_video_file(self):
        video_file = self.cleaned_data.get('video_file')
        
        if video_file:
            # ファイル拡張子をチェック
            file_extension = os.path.splitext(video_file.name)[1].lower()
            if file_extension != '.mp4':
                raise ValidationError('MP4形式のファイルのみアップロード可能です。')
            
            # MIMEタイプをチェック
            if video_file.content_type != 'video/mp4':
                raise ValidationError('MP4形式のファイルのみアップロード可能です。')
            
            # ファイルサイズをチェック（128GB制限）
            max_size = 128 * 1024 * 1024 * 1024  # 128GB in bytes
            if video_file.size > max_size:
                raise ValidationError('ファイルサイズは128GB以下にしてください。')
        
        return video_file
    
    def clean(self):
        cleaned_data = super().clean()
        is_paid = cleaned_data.get('is_paid')
        price = cleaned_data.get('price')
        video_file = cleaned_data.get('video_file')
        is_shorts = cleaned_data.get('is_shorts')
        
        if is_paid and not price:
            raise ValidationError('有料コンテンツの場合、価格を設定してください。')
        
        if is_paid and price and price < 100:
            raise ValidationError('価格は100円以上に設定してください。')
        
        if not is_paid and price:
            # If not paid but price is set, clear the price
            cleaned_data['price'] = None
        
        # 動画の長さを自動計算（FFprobeが利用可能な場合のみ）
        if video_file:
            try:
                duration = get_video_duration(video_file)
                if duration:
                    cleaned_data['duration'] = duration
                    
                    # ショート動画として指定された場合の制限チェック
                    if is_shorts and duration > 60:
                        raise ValidationError('ショート動画は60秒以下の動画のみ設定できます。')
                    
                    # 60秒以下の動画は自動的にショート動画に設定
                    if duration <= 60:
                        cleaned_data['is_shorts'] = True
                        
            except Exception:
                # FFprobeが利用できない場合はスキップ
                pass
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # cleaned_dataから duration を取得
        if hasattr(self, 'cleaned_data') and 'duration' in self.cleaned_data:
            instance.duration = self.cleaned_data['duration']
        
        if commit:
            instance.save()
        return instance
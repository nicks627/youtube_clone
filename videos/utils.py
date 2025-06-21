import subprocess
import json
import os
from django.core.files.storage import default_storage

def get_video_duration(video_file):
    """
    FFprobeを使用して動画ファイルの長さを取得する
    
    Args:
        video_file: UploadedFile object または file path
    
    Returns:
        int: 動画の長さ（秒）、取得できない場合はNone
    """
    try:
        # ファイルパスを取得
        if hasattr(video_file, 'temporary_file_path'):
            # UploadedFile の場合
            file_path = video_file.temporary_file_path()
        elif hasattr(video_file, 'path'):
            # FileField の場合
            file_path = video_file.path
        else:
            # 文字列パスの場合
            file_path = str(video_file)
        
        # ファイルが存在するかチェック
        if not os.path.exists(file_path):
            return None
        
        # FFprobeコマンドを実行
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return None
        
        # JSONレスポンスをパース
        data = json.loads(result.stdout)
        
        # formatセクションから duration を取得
        if 'format' in data and 'duration' in data['format']:
            duration = float(data['format']['duration'])
            return int(duration)
        
        # streamsセクションからビデオストリームの duration を取得
        if 'streams' in data:
            for stream in data['streams']:
                if stream.get('codec_type') == 'video' and 'duration' in stream:
                    duration = float(stream['duration'])
                    return int(duration)
        
        return None
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError, ValueError, FileNotFoundError):
        return None

def format_duration(seconds):
    """
    秒数を HH:MM:SS または MM:SS フォーマットに変換
    
    Args:
        seconds (int): 秒数
    
    Returns:
        str: フォーマットされた時間文字列
    """
    if not seconds:
        return "0:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def extract_video_thumbnail(video_file, output_path, time_offset=1):
    """
    FFmpegを使用して動画からサムネイルを抽出
    
    Args:
        video_file: 動画ファイルのパス
        output_path: 出力サムネイルのパス
        time_offset: サムネイルを取得する時点（秒）
    
    Returns:
        bool: 成功した場合True、失敗した場合False
    """
    try:
        # ファイルパスを取得
        if hasattr(video_file, 'path'):
            file_path = video_file.path
        else:
            file_path = str(video_file)
        
        if not os.path.exists(file_path):
            return False
        
        # FFmpegコマンドを実行
        cmd = [
            'ffmpeg',
            '-i', file_path,
            '-ss', str(time_offset),
            '-vframes', '1',
            '-q:v', '2',
            '-y',  # overwrite output file
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        return result.returncode == 0 and os.path.exists(output_path)
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return False
import subprocess
import os
import uuid

class VideoMixer:
    def __init__(self):
        self.temp_dir = "videos/temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    def concatenate_videos(self, video_paths: list) -> str:
        list_file = os.path.join(self.temp_dir, "input.txt")
        output_file = os.path.join("videos", f"sequence_{uuid.uuid4().hex[:8]}.mp4")
        
        with open(list_file, "w") as f:
            for path in video_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
        
        subprocess.run([
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_file,
            "-y"
        ], check=True)
        
        return output_file

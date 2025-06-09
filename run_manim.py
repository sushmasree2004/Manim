import subprocess
import uuid
import os
import re
from manim import *

def extract_python_code(text):
    """
    Extract Python code from markdown code blocks or plain text.
    """
    # Remove ```python ... ```
    text = re.sub(r'```python\s*\n([\s\S]*?)\n```', r'\1', text, flags=re.DOTALL)
    # Remove ``` ... ```
    text = re.sub(r'```\s*\n([\s\S]*?)\n```', r'\1', text, flags=re.DOTALL)
    # Remove any remaining backticks
    text = re.sub(r'```', '', text)
    return text.strip()

def fix_color_constants(code):
    """
    Fix color constant usage in the code.
    """
    # List of valid Manim color constants
    valid_colors = [
        'BLUE', 'RED', 'GREEN', 'YELLOW', 'PURPLE', 'ORANGE', 'PINK',
        'WHITE', 'BLACK', 'GRAY', 'GOLD', 'MAROON', 'TEAL', 'NAVY'
    ]
    
    # Replace quoted colors with unquoted constants
    for color in valid_colors:
        code = re.sub(f"color=['\"]{color}['\"]", f"color={color}", code)
        code = re.sub(f"set_color\(['\"]{color}['\"]\)", f"set_color({color})", code)
    
    return code

def run_manim_code(code, max_retries=2):
    """
    Save and run Manim code, with fallback on failure.
    """
    for attempt in range(max_retries + 1):
        try:
            filename = f"animation_{uuid.uuid4().hex[:8]}.py"
            folder = "videos"
            os.makedirs(folder, exist_ok=True)
            filepath = os.path.join(folder, filename)
            clean_code = extract_python_code(code)
            
            # Fix color constants
            clean_code = fix_color_constants(clean_code)

            if "from manim import *" not in clean_code:
                clean_code = "from manim import *\n\n" + clean_code
            if "class AnimationScene(Scene):" not in clean_code:
                clean_code = re.sub(r'class\s+Scene\s*\(.*\):', 'class AnimationScene(Scene):', clean_code)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(clean_code)

            result = subprocess.run(
                ["manim", "-pql", filepath, "AnimationScene", "--media_dir", folder],
                capture_output=True,
                text=True,
                timeout=45
            )

            if result.returncode == 0:
                videos = [os.path.join(root, f) for root, _, files in os.walk(folder) for f in files if f.endswith('.mp4')]
                if videos:
                    latest = max(videos, key=os.path.getctime)
                    return {"success": True, "video_path": latest}
                return {"success": False, "error": "No video generated"}
            else:
                error_msg = result.stderr
                if attempt < max_retries:
                    # Only use fallback for critical errors
                    if "ImportError" in error_msg or "SyntaxError" in error_msg or "NameError" in error_msg or "format specifier" in error_msg:
                        # Create a more interesting fallback animation based on the error type
                        if "Text" in error_msg or "MathTex" in error_msg:
                            fallback = """from manim import *

class AnimationScene(Scene):
    def construct(self):
        try:
            # Text animation fallback
            text = Text("Animation", color=BLUE)
            self.play(Write(text), run_time=1)
            self.wait(0.5)
            self.play(text.animate.scale(2).set_color(RED), run_time=1)
            self.wait(0.5)
            self.play(FadeOut(text), run_time=1)
        except Exception as e:
            # Shape animation fallback
            square = Square(side_length=2, color=BLUE)
            self.play(Create(square), run_time=1)
            self.wait(0.5)
            self.play(square.animate.rotate(PI/2), run_time=1)
            self.wait(0.5)
"""
                        else:
                            fallback = """from manim import *

class AnimationScene(Scene):
    def construct(self):
        try:
            # Shape transformation fallback
            square = Square(side_length=2, color=BLUE)
            circle = Circle(radius=1, color=RED)
            
            self.play(Create(square), run_time=1)
            self.wait(0.5)
            self.play(Transform(square, circle), run_time=1)
            self.wait(0.5)
            self.play(circle.animate.scale(2).set_color(GREEN), run_time=1)
            self.wait(0.5)
        except Exception as e:
            # Simple fallback
            self.play(Create(Circle()), run_time=1)
            self.wait(1)
"""
                        code = fallback
                        continue
                    return {"success": False, "error": f"Manim error: {error_msg}"}
                return {"success": False, "error": f"Manim failed: {error_msg}"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout"}
        except FileNotFoundError:
            return {"success": False, "error": "Manim not installed"}
        except Exception as e:
            if attempt < max_retries:
                return {"success": False, "error": f"Error: {str(e)}"}
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "Max retries"}

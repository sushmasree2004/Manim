from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from langchain_setup import manim_agent
from run_manim import run_manim_code
from video_mixer import VideoMixer
import os
import traceback

app = FastAPI(title="Manim Video Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.post("/generate")
async def generate(prompt: str = Form(...)):
    try:
        result = manim_agent.workflow.invoke({"user_prompt": prompt, "retry_count": 0})
        if result["execution_result"]["success"]:
            return {"success": True, "video_url": f"/video?file={result['execution_result']['video_path']}"}
        return {"success": False, "error": result["execution_result"].get("error", "Unknown error")}
    except Exception as e:
        return {"success": False, "error": f"Server error: {str(e)}"}

@app.post("/generate_and_merge")
async def generate_and_merge(prompts: list[str] = Form(...)):
    mixer = VideoMixer()
    video_paths = []

    for prompt in prompts:
        result = manim_agent.workflow.invoke({"user_prompt": prompt, "retry_count": 0})
        if result["execution_result"]["success"]:
            video_paths.append(result["execution_result"]["video_path"])
        else:
            return JSONResponse({
                "success": False,
                "error": f"Failed to generate video for prompt: {prompt}"
            }, status_code=400)

    if not video_paths:
        raise HTTPException(400, "No valid videos generated")

    try:
        final_path = mixer.concatenate_videos(video_paths)
        return JSONResponse({
            "success": True,
            "video_url": f"/video?file={final_path}"
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": f"Video merging failed: {str(e)}"
        }, status_code=500)

@app.post("/merge_videos")
async def merge_videos(request: Request):
    data = await request.json()
    video_paths = data.get("video_paths", [])
    if not video_paths:
        return JSONResponse({"success": False, "error": "No videos selected"}, status_code=400)
    mixer = VideoMixer()
    try:
        final_path = mixer.concatenate_videos(video_paths)
        return JSONResponse({
            "success": True,
            "video_url": f"/video?file={final_path}"
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": f"Video merging failed: {str(e)}"
        }, status_code=500)

@app.get("/video")
async def get_video(file: str):
    if os.path.exists(file):
        return FileResponse(file, media_type="video/mp4")
    return {"error": "Video not found"}

@app.post("/delete_video")
async def delete_video(request: Request):
    data = await request.json()
    video_path = data.get("video_path")
    if not video_path or not os.path.exists(video_path):
        return JSONResponse({"success": False, "error": "File not found."}, status_code=404)
    try:
        os.remove(video_path)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

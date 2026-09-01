"""
AG VIDEO MODULE — standalone product-demo-video system
=========================================================
This is the EXACT SAME video system used on AG TradeBridge for EA/
indicator demo videos: Range-request support (needed for iPhone/
Safari) + a click-to-expand dark lightbox popup player.

HOW TO INSTALL IN A NEW PROJECT
--------------------------------------------------------------
1. Copy this file into the project root.
2. In the main FastAPI file, right after `app = FastAPI()`:

     from video_module import video_router, add_video, video_popup_html
     app.include_router(video_router)

3. For EACH video, compress it first (keep full length/speed —
   only reduce file size), then register it:

     add_video("demo1", "/path/to/compressed_demo.mp4")
     # this creates a working route at:  GET /video/demo1.mp4

4. In your product HTML, show the video with the SAME expand-to-
   popup behavior as the original site:

     <div style="position:relative">
       <video controls playsinline preload="metadata"
              style="width:100%;border-radius:10px;background:#000"
              src="/video/demo1.mp4"></video>
       <div onclick="videoLB('/video/demo1.mp4')"
            style="position:absolute;top:10px;right:10px;width:36px;height:36px;
            border-radius:50%;background:rgba(0,0,0,.55);color:#f7c04a;
            display:flex;align-items:center;justify-content:center;
            font-size:16px;cursor:pointer">⛶</div>
     </div>

5. Paste `video_popup_html()` ONCE near the end of every page's
   <body> (it injects the lightbox + the `videoLB()` / `closeVideoLB()`
   JS functions — same as the original site):

     <script> ... </script>  <!-- your page's own scripts -->
     {video_popup_html()}
     </body></html>

--------------------------------------------------------------
TO ATTACH THE ACTUAL VIDEO FILES
--------------------------------------------------------------
add_video() reads bytes from a file path and stores them in memory
(VIDEOS dict below) — that's all the original site did too (videos
were base64-embedded into media_data.py at deploy time). If you're
handing this project to someone else, give them this file PLUS the
actual .mp4 files, and they call add_video() once per file.
"""

from fastapi import APIRouter, Request
from fastapi.responses import Response

video_router = APIRouter()

VIDEOS = {}   # {video_id: raw_mp4_bytes}


def add_video(video_id: str, path_or_bytes):
    """path_or_bytes: a filesystem path (str) OR raw bytes."""
    if isinstance(path_or_bytes, (bytes, bytearray)):
        VIDEOS[video_id] = bytes(path_or_bytes)
    else:
        with open(path_or_bytes, "rb") as f:
            VIDEOS[video_id] = f.read()


def _serve_video(request: Request, data: bytes):
    """Exact original helper — adds HTTP Range support (206 Partial
       Content) which iPhone/Safari require to play video at all."""
    total = len(data)
    range_header = request.headers.get("range") or request.headers.get("Range")
    if range_header and range_header.strip().lower().startswith("bytes="):
        try:
            rng = range_header.split("=", 1)[1].split(",")[0].strip()
            start_s, _, end_s = rng.partition("-")
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else total - 1
            if start < 0:
                start = 0
            if end >= total:
                end = total - 1
            if start > end:
                start = 0
            chunk = data[start:end + 1]
            return Response(
                content=chunk,
                status_code=206,
                media_type="video/mp4",
                headers={
                    "Content-Range": f"bytes {start}-{end}/{total}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(len(chunk)),
                    "Cache-Control": "public, max-age=86400",
                },
            )
        except Exception:
            pass
    return Response(
        content=data,
        media_type="video/mp4",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Accept-Ranges": "bytes",
            "Content-Length": str(total),
        },
    )


@video_router.get("/video/{video_id}.mp4")
async def serve_video(video_id: str, request: Request):
    data = VIDEOS.get(video_id)
    if not data:
        return Response(content=b"", status_code=404)
    return _serve_video(request, data)


def video_popup_html():
    """Paste this once near </body> on every page that shows videos.
       Gives you the dark lightbox popup + videoLB()/closeVideoLB()
       JS — identical to the original site's behavior."""
    return """
<div id="vlb" onclick="if(event.target.id==='vlb')closeVideoLB()" style="display:none;position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.94);align-items:center;justify-content:center;padding:20px">
  <video id="vlbvid" controls playsinline autoplay style="max-width:94%;max-height:90%;width:auto;border-radius:16px;background:#000;box-shadow:0 20px 60px rgba(0,0,0,.7),0 0 0 1px rgba(212,175,55,.25),0 0 60px rgba(212,175,55,.12);border:2px solid rgba(212,175,55,.3)"></video>
  <div onclick="closeVideoLB()" style="position:absolute;top:24px;right:28px;color:#fff;font-size:22px;line-height:1;cursor:pointer;width:44px;height:44px;border-radius:50%;background:rgba(255,255,255,.1);backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center;border:1px solid rgba(255,255,255,.2)">&times;</div>
</div>
<script>
function videoLB(src){var b=document.getElementById('vlb'),v=document.getElementById('vlbvid');v.src=src;b.style.display='flex';v.play().catch(function(){});}
function closeVideoLB(){var b=document.getElementById('vlb'),v=document.getElementById('vlbvid');v.pause();v.removeAttribute('src');v.load();b.style.display='none';}
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeVideoLB();});
</script>
"""

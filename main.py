import os, uuid, shutil, subprocess, tempfile
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if API_KEY else None
ROOT = Path(__file__).resolve().parent
WORK = ROOT / "jobs"
WORK.mkdir(exist_ok=True)
app = FastAPI(title="Auto Myanmar Video Tool")
app.mount("/static", StaticFiles(directory=ROOT.parent / "frontend"), name="static")

def require_tools():
    if not client:
        raise HTTPException(500, "OPENAI_API_KEY မထည့်ရသေးပါ။ backend/.env ကို စစ်ဆေးပါ။")
    if not shutil.which("ffmpeg"):
        raise HTTPException(500, "FFmpeg မတွေ့ပါ။ FFmpeg ကို install လုပ်ပြီး PATH ထဲထည့်ပါ။")

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-2500:])

def srt_time(seconds):
    ms = int(max(0, seconds) * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def write_srt(segments, path):
    lines = []
    for i, seg in enumerate(segments, 1):
        start = float(seg["start"])
        end = max(start + 0.5, float(seg["end"]))
        lines += [str(i), f"{srt_time(start)} --> {srt_time(end)}", seg["myanmar"], ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")

@app.get("/", response_class=HTMLResponse)
def home():
    return (ROOT.parent / "frontend" / "index.html").read_text(encoding="utf-8")

@app.post("/api/process")
async def process_video(
    video: UploadFile = File(...),
    voice_gender: str = Form("female"),
    subtitle: str = Form("burn")
):
    require_tools()
    suffix = Path(video.filename or "video.mp4").suffix.lower()
    if suffix not in [".mp4", ".mov", ".m4v", ".webm"]:
        raise HTTPException(400, "MP4, MOV, M4V သို့မဟုတ် WEBM ဖိုင်သာ ထည့်ပါ။")
    job_id = str(uuid.uuid4())[:8]
    job = WORK / job_id
    job.mkdir()
    input_path = job / f"input{suffix}"
    with input_path.open("wb") as f:
        shutil.copyfileobj(video.file, f)

    try:
        audio_path = job / "source_audio.mp3"
        run(["ffmpeg", "-y", "-i", str(input_path), "-vn", "-ac", "1", "-ar", "16000", str(audio_path)])

        # Whisper transcription with segment timestamps
        with audio_path.open("rb") as af:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", file=af, response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
        raw_segments = getattr(transcript, "segments", None) or []
        if not raw_segments:
            raise RuntimeError("အသံစာသား မရရှိပါ။ ပိုတိုသော video ဖြင့် ထပ်စမ်းပါ။")

        segments = []
        # Translate in small batches to keep context and avoid overly long prompts.
        for seg in raw_segments:
            source_text = (seg.text or "").strip()
            if not source_text:
                continue
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.2,
                messages=[
                    {"role":"system","content":"သင်သည် မြန်မာဘာသာပြန်သူဖြစ်သည်။ အောက်ပါ စကားပြောစာသားကို အဓိပ္ပာယ်မပျောက်စေဘဲ သဘာဝကျသော ပြောစကားမြန်မာလို ပြန်ပါ။ အပိုရှင်းပြချက်၊ ခေါင်းစဉ်၊ မူရင်းဘာသာစကား မထည့်ပါနှင့်။ နာမည်များကို အခြေအနေအလိုက် အသံထွက်နီးစပ်စွာ ရေးပါ။"},
                    {"role":"user","content":source_text}
                ]
            )
            translated = response.choices[0].message.content.strip()
            segments.append({"start": float(seg.start), "end": float(seg.end), "source": source_text, "myanmar": translated})

        if not segments:
            raise RuntimeError("ဘာသာပြန်ရန် စာသားမတွေ့ပါ။")

        srt_path = job / "myanmar_subtitles.srt"
        write_srt(segments, srt_path)

        voice = os.getenv("FEMALE_TTS_VOICE", "nova") if voice_gender == "female" else os.getenv("MALE_TTS_VOICE", "onyx")
        # Generate per-segment audio to preserve ordering. This first MVP concatenates
        # speech clips; precise time-stretch/alignment can be added in the next iteration.
        audio_parts = []
        for i, seg in enumerate(segments):
            out = job / f"voice_{i:04}.mp3"
            with client.audio.speech.with_streaming_response.create(
                model="tts-1", voice=voice, input=seg["myanmar"], response_format="mp3"
            ) as response:
                response.stream_to_file(out)
            audio_parts.append(out)

        # Place each translated speech clip near its original segment start time.
        # This is a basic alignment strategy; long translations may still overlap.
        dubbed = job / "myanmar_voice.mp3"
        if len(audio_parts) == 1:
            run(["ffmpeg", "-y", "-i", str(audio_parts[0]), "-c:a", "libmp3lame", str(dubbed)])
        else:
            inputs = []
            filters = []
            for i, (part, seg) in enumerate(zip(audio_parts, segments)):
                inputs += ["-i", str(part)]
                delay = max(0, int(float(seg["start"]) * 1000))
                filters.append(f"[{i}:a]adelay={delay}|{delay}[a{i}]")
            mix_inputs = "".join(f"[a{i}]" for i in range(len(audio_parts)))
            filters.append(f"{mix_inputs}amix=inputs={len(audio_parts)}:duration=longest:normalize=0[out]")
            run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters),
                 "-map", "[out]", "-c:a", "libmp3lame", str(dubbed)])

        output_path = job / "output_myanmar.mp4"
        if subtitle == "burn":
            # Escape subtitle path for ffmpeg filter syntax.
            escaped = str(srt_path).replace("\\\\", "/").replace(":", "\\\\:")
            vf = f"subtitles='{escaped}':force_style='FontName=Noto Sans Myanmar,FontSize=20,Outline=1,Shadow=0,Alignment=2,MarginV=28'"
            run(["ffmpeg", "-y", "-i", str(input_path), "-i", str(dubbed),
                 "-map", "0:v:0", "-map", "1:a:0", "-vf", vf,
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                 "-c:a", "aac", "-shortest", str(output_path)])
        else:
            run(["ffmpeg", "-y", "-i", str(input_path), "-i", str(dubbed),
                 "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                 "-c:a", "aac", "-shortest", str(output_path)])

        return {
            "job_id": job_id,
            "message": "ပြီးပါပြီ။ အောက်ပါဖိုင်များကို ရယူနိုင်ပါပြီ။",
            "video_url": f"/api/download/{job_id}/output_myanmar.mp4",
            "subtitle_url": f"/api/download/{job_id}/myanmar_subtitles.srt",
            "voice_url": f"/api/download/{job_id}/myanmar_voice.mp3",
            "segments": len(segments)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"လုပ်ဆောင်ရာတွင် အမှားဖြစ်နေပါတယ်: {str(e)}")

@app.get("/api/download/{job_id}/{filename}")
def download(job_id: str, filename: str):
    allowed = {"output_myanmar.mp4", "myanmar_subtitles.srt", "myanmar_voice.mp3"}
    if filename not in allowed:
        raise HTTPException(404, "ဖိုင်မတွေ့ပါ။")
    path = WORK / job_id / filename
    if not path.exists():
        raise HTTPException(404, "ဖိုင်မတွေ့ပါ။")
    return FileResponse(path, filename=filename)

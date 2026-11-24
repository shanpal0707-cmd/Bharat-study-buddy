
import os
import requests
from dotenv import load_dotenv

# Load existing Groq API key from project root .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def transcribe_video(video_path):

    try:
        if not os.path.isfile(video_path):
            raise FileNotFoundError(
                f"Video file not found: {video_path}"
            )

        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY not found in .env file."
            )

        file_size = os.path.getsize(video_path)

        # Groq API file limit
        if file_size > 25 * 1024 * 1024:
            raise RuntimeError(
                "Video exceeds Groq's 25 MB upload limit. "
                "Please use a smaller video."
            )

        print("Starting Groq video transcription...")

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }

        data = {
            "model": "whisper-large-v3-turbo",
            "response_format": "verbose_json",
            "timestamp_granularities[]": "segment"
        }

        with open(video_path, "rb") as video_file:

            files = {
                "file": (
                    os.path.basename(video_path),
                    video_file
                )
            }

            response = requests.post(
                GROQ_URL,
                headers=headers,
                data=data,
                files=files,
                timeout=300
            )

        if response.status_code != 200:
            print("Groq API error:", response.text)

            raise RuntimeError(
                f"Groq API returned {response.status_code}: "
                f"{response.text[:500]}"
            )

        result = response.json()

        print(
            "Detected language:",
            result.get("language", "Unknown")
        )

        transcript = []

        for segment in result.get("segments", []):

            text = segment.get("text", "").strip()

            if not text:
                continue

            transcript.append({
                "source": "VIDEO",
                "start": round(float(segment.get("start", 0)), 2),
                "end": round(float(segment.get("end", 0)), 2),
                "text": text
            })

        if not transcript:
            raise RuntimeError(
                "No speech detected or no transcript returned."
            )

        print(
            f"Groq transcription completed: "
            f"{len(transcript)} segments"
        )

        return transcript

    except Exception as error:

        print("Groq video processing error:", repr(error))

        raise RuntimeError(
            f"Video transcription failed: {error}"
        ) from error

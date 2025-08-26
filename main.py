from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.pipeline import CheckNERPipeline
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO
from datetime import datetime
from num2words import num2words

app = FastAPI()
pipeline = CheckNERPipeline(whisper_model_name="medium")  

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/home.html", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.post("/process_audio")
async def process_audio(file: UploadFile = File(...)):
    temp_input = "temp/input_audio.webm"
    audio_path = "temp/recording.wav"
    output_image_path = "app/static/filled_check.jpg"
    os.makedirs(os.path.dirname(temp_input), exist_ok=True)
    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)

    submission_date = datetime.now().strftime("%B %d, %Y")  

    # Save uploaded file
    with open(temp_input, "wb") as f:
        content = await file.read()
        print(f"Received file size: {len(content)} bytes, content type: {file.content_type}")
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        f.write(content)

    # Convert to WAV
    try:
        cmd = [
            "ffmpeg", "-y", "-i", temp_input,
            "-f", "wav", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_path
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"FFmpeg output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Failed to convert audio: {e.stderr}")

    # Verify WAV file
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        raise HTTPException(status_code=500, detail="Converted WAV file is empty or invalid")

    # Process with Whisper and NER
    try:
        result = pipeline.process_audio(audio_path)
        transcription = result["transcription"]
        entities = result["entities"]
        print(f"Transcription: {transcription}")
        print(f"Detected entities: {entities}")

        # Extract payee, amount, and date
        payee_name = next((e["text"].strip(".") for e in entities if e["label"] == "PAYEE_NAME"), None)
        amount_entity = next((e for e in entities if e["label"] == "AMOUNT" and e.get("parsed")), None)
        amount = amount_entity["parsed"][0]["value"] if amount_entity and amount_entity.get("parsed") else None
        written_amount = amount_entity["written_amount"] if amount_entity and "written_amount" in amount_entity else "No Amount"

        if not payee_name:
            payee_name = "Unknown Payee"

        # Add entities to check.JPG
        try:
            image = Image.open("app/static/check.JPG")
            draw = ImageDraw.Draw(image)
            try:
                font_path = "app/static/DejaVuSans.ttf"
                font = ImageFont.truetype(font_path, 14)
            except IOError:
                print("Warning: Failed to load DejaVuSans.ttf, using default font with size 24")
                font = ImageFont.load_default().font_variant(size=20)

            # Coordinates (adjust based on check.JPG layout)
            payee_coords = (190, 110)
            amount_numeric_coords = (578, 110)
            amount_written_coords = (90, 150)
            date_coords = (510, 45)
            signature=(510,220)

            signature_font_path = "app/static/Bastliga One.ttf"  
            if not os.path.exists(signature_font_path):
                print(f"Warning: {signature_font_path} not found, using default font for signature")
                signature_font = ImageFont.load_default().font_variant(size=24)
            else:
                signature_font = ImageFont.truetype(signature_font_path, 24) 

            signature_text = "Kiran"
            # Add payee name
            draw.text(payee_coords, payee_name, fill="black", font=font)
            # add signature
            draw.text(signature,signature_text,fill='black',font=signature_font)
            if amount is not None:
                print(f"Raw amount before conversion: {amount}")
                draw.text(amount_numeric_coords, f"{amount:.2f}", fill="black", font=font)
                print(f"Written amount: {written_amount}")
                draw.text(amount_written_coords, written_amount, fill="black", font=font)
            else:
                draw.text(amount_numeric_coords, "0.00", fill="black", font=font)
                draw.text(amount_written_coords, "No Amount", fill="black", font=font)

            # Add date
            draw.text(date_coords, submission_date, fill="black", font=font)

            # Save the modified image
            image.save(output_image_path, "JPEG", quality=95)
            print(f"Saved image to {output_image_path}")

            # Convert image to base64 for frontend
            buffered = BytesIO()
            image.save(buffered, format="JPEG", quality=95)
            image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        except Exception as e:
            print(f"Image processing error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")

    finally:
        # Clean up files
        for path in [temp_input, audio_path]:
            if os.path.exists(path):
                os.remove(path)

    return {
        "transcription": transcription,
        "image": f"data:image/jpeg;base64,{image_base64}",
        "image_path": "/static/filled_check.jpg",
        "entities": entities  
    }
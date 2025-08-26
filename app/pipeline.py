from faster_whisper import WhisperModel
import spacy
from num2words import num2words
import re
import os

class CheckNERPipeline:
    def __init__(self, whisper_model_name="medium", ner_model_path="app/model/fine_tuned_ner"):
        try:
            self.whisper_model = WhisperModel(whisper_model_name, device="cpu", compute_type="int8")
            print(f"Loaded faster-whisper model: {whisper_model_name}")
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            raise

        try:
            self.nlp = spacy.load(ner_model_path)
            print(f"Loaded NER model from {ner_model_path}")
        except Exception as e:
            print(f"Error loading NER model: {e}")
            raise

    def transcribe_audio(self, audio_path):
        try:
            segments, _ = self.whisper_model.transcribe(audio_path, language="en", task="transcribe")
            transcription = " ".join(segment.text for segment in segments)
            return transcription
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return ""

    def process_audio(self, audio_path):
        transcription = self.transcribe_audio(audio_path)
        if not transcription:
            return {"transcription": "", "entities": []}

        # Pre-process transcription
        transcription = transcription.lower().replace("$", "")
        if "and" in transcription and "cents" in transcription:
            amount_match = re.search(r'(\d+)\s+and\s+(\d+)\s+cents', transcription)
            if amount_match:
                whole = int(amount_match.group(1))
                cents = int(amount_match.group(2))
                transcription = transcription.replace(amount_match.group(0), f"{whole}.{str(cents).zfill(2)}")

        doc = self.nlp(transcription)
        entities = []
        
        for ent in doc.ents:
            entity_dict = {"text": ent.text.strip(".,$"), "label": ent.label_}
            if ent.label_ == "AMOUNT":
                amount_text = ent.text.lower()  
                try:
                    value = float(re.sub(r'[^\d.]', '', amount_text))  # Base numeric value
                    # Handle multipliers
                    if "million" in amount_text:
                        value *= 100000
                    elif "thousand" in amount_text:
                        value *= 1000
                    value = round(value, 2)  # Ensure two decimal places
                    entity_dict["parsed"] = [{"original": ent.text, "value": value}]
                    integer_part = int(value)
                    decimal_part = int((value - integer_part) * 100)
                    decimal_words = "zero zero" if decimal_part == 0 else num2words(decimal_part).lower()
                    entity_dict["written_amount"] = f"{num2words(integer_part).capitalize()} point {decimal_words}"
                except ValueError:
                    print(f"Failed to parse '{ent.text}' as number")
                    entity_dict["parsed"] = []
            entities.append(entity_dict)
        
        if "to" in transcription:
            to_index = transcription.index("to") + 3
            potential_payee = transcription[to_index:].strip(".,")
            if potential_payee and not any(e["label"] == "PAYEE_NAME" for e in entities):
                entities.append({"text": potential_payee, "label": "PAYEE_NAME"})
        
        if not any(e["label"] == "AMOUNT" for e in entities):
            amount_match = re.search(r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?', transcription)
            if amount_match:
                amount_text = amount_match.group().replace(",", "")
                try:
                    value = float(amount_text)
                    value = round(value, 2)
                    entities.append({
                        "text": amount_match.group(),
                        "label": "AMOUNT",
                        "parsed": [{"original": amount_match.group(), "value": value}],
                        "written_amount": f"{num2words(int(value)).capitalize()} point {'zero zero' if int((value - int(value)) * 100) == 0 else num2words(int((value - int(value)) * 100)).lower()}"
                    })
                except ValueError:
                    print(f"Failed to parse '{amount_match.group()}' as number")

        print(f"Extracted entities: {entities}")
        return {"transcription": transcription, "entities": entities}
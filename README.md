1. Introduction
The Auto-Check System is designed to automate the process of cheque writing and verification.
It combines speech recognition and natural language processing to capture user input, extract important cheque details, and automatically fill a cheque template image.
This reduces manual effort and minimizes errors in financial document processing.


2. Objectives
Convert speech to text using Faster Whisper.
Extract cheque fields such as Payee Name, Amount, and Date using spaCy NER.
Automatically fill these extracted details onto a cheque image template.
Provide CLI and API interfaces for user interaction.
3. Methodology
Input: User provides cheque details via speech.
ASR (Faster Whisper): Transcribes audio into text.
NER (spaCy): Identifies PAYEE_NAME, AMOUNT, and DATE.
Post-processing: Normalizes amount, cleans names, and assigns the current date.
Cheque Filling: Extracted details are written onto a cheque image.
Output: JSON result + cheque image with filled details.


4. Results
Example Input (Speech)
"Write a cheque of 2,000 to Garima Saud"
Extracted Entities
Payee Name → Garima 
Amount → 2000.00
Date → current date

Output
✔ Cheque image filled with extracted fields

6. Conclusion
The project demonstrates the integration of speech-to-text (ASR) and NLP (NER) for automating cheque processing.
It can be extended to support multiple currencies, different languages, and signature placement, making it suitable for future smart banking applications.

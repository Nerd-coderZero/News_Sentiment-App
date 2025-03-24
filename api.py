from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import glob
import json
import pickle
import pandas as pd
import logging
from fastapi.responses import FileResponse
from utils.news_scraper import NewsScraper
from utils.gemini_service import GeminiService
from utils.text_to_speech import TextToSpeechService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
google_api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
translator_type = os.getenv("TRANSLATOR_TYPE", "fallback")
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Initialize Gemini and TTS globally
if gemini_api_key:
    gemini_service = GeminiService(api_key=gemini_api_key)
else:
    logging.warning("GEMINI_API_KEY not found in environment variables. Some functionality may be limited.")
    gemini_service = None

tts_service = TextToSpeechService(gemini_service=gemini_service)

# FastAPI app
app = FastAPI(title="News Sentiment Analysis API", version="1.0.0")

# Pydantic Models
class CompanyRequest(BaseModel):
    company_name: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the News Sentiment Analysis API", "version": "1.0.0"}

@app.get("/companies")
def get_companies():
    try:
        company_list_path = os.path.join("data", "company_list.csv")
        if os.path.exists(company_list_path):
            df = pd.read_csv(company_list_path)
            companies = df["company"].tolist()
        else:
            files = glob.glob(os.path.join("data", "output", "*.pkl"))
            companies = [os.path.basename(f).replace(".pkl", "").replace("_", " ").title() for f in files]

        if not companies:
            companies = ["Tesla", "Apple", "Microsoft", "Google", "Amazon"]
        return {"companies": companies}
    except Exception as e:
        logging.error(f"Error getting companies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/company/{company_name}")
def get_company_analysis(company_name: str):
    try:
        file_name = company_name.lower().replace(" ", "_")
        file_path = os.path.join("data", "output", f"{file_name}.pkl")
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = pickle.load(f)
            return data
        else:
            raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")
    except Exception as e:
        logging.error(f"Error getting analysis for {company_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio/{company_name}")
async def get_company_audio(company_name: str):
    company_slug = company_name.lower().replace(' ', '_')
    audio_path = os.path.join("data", "output", "audio", f"{company_slug}.mp3")
    text_path = os.path.join("data", "output", "text", f"{company_slug}_hindi.txt")

    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    hindi_text = ""
    if os.path.exists(text_path):
        with open(text_path, 'r', encoding='utf-8') as f:
            hindi_text = f.read()

    return {
        "audio_url": f"/download-audio/{company_slug}",
        "hindi_text": hindi_text
    }

@app.get("/download-audio/{company_slug}")
async def download_audio(company_slug: str):
    audio_path = os.path.join("data", "output", "audio", f"{company_slug}.mp3")
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(audio_path, media_type="audio/mpeg", filename=f"{company_slug}.mp3")

@app.post("/analyze")
async def analyze_company(data: CompanyRequest):
    company_name = data.company_name
    try:
        if not gemini_service:
            logging.error("Gemini API key is missing. Please provide a valid API key.")
            raise HTTPException(status_code=500, detail="Gemini API key is missing. Please provide a valid API key.")

        news_scraper = NewsScraper()
        articles = news_scraper.search_company_news(company_name, max_results=10)
        if not articles:
            logging.warning(f"No articles found for {company_name}")
            raise HTTPException(status_code=404, detail="No articles found.")

        analysis_result = {"Company": company_name, "Articles": []}
        for article in articles:
            title = article.get("title", "No Title")
            content = article.get("content", "")
            article_analysis = gemini_service.analyze_article(title, content)
            if article_analysis:
                analysis_result["Articles"].append(article_analysis)

        if analysis_result["Articles"]:
            comp_analysis = gemini_service.generate_comparative_analysis(company_name, analysis_result["Articles"])
            final_sentiment = gemini_service.generate_final_sentiment(company_name, analysis_result)

            analysis_result["Comparative Sentiment Score"] = comp_analysis
            analysis_result["Final Sentiment Analysis"] = final_sentiment

            # Save result
            file_name = company_name.lower().replace(" ", "_")
            file_path = os.path.join("data", "output", f"{file_name}.pkl")
            with open(file_path, "wb") as f:
                pickle.dump(analysis_result, f)

            # Generate Hindi TTS
            if final_sentiment:
                audio_path = os.path.join("data", "output", "audio", f"{file_name}.mp3")
                text_path = os.path.join("data", "output", "text", f"{file_name}_hindi.txt")
                audio_file, hindi_text = tts_service.generate_hindi_speech_from_english(final_sentiment, audio_path)
                if hindi_text:
                    with open(text_path, 'w', encoding='utf-8') as f:
                        f.write(hindi_text)
            else:
                logging.warning(f"No final sentiment analysis available for {company_name}")

            return analysis_result
        else:
            logging.error(f"Failed to analyze articles for {company_name}")
            raise HTTPException(status_code=500, detail="Failed to analyze articles.")
    except Exception as e:
        logging.error(f"Error analyzing company: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
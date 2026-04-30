import joblib
import pandas as pd
import numpy as np
import os
import json
import logging
from google import genai
from django.conf import settings
from analytics.ml_logic import BehavioralFeatureEngineer   # keeps joblib happy
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)

import threading
import sys

_reg_pipeline = None
_clf_pipeline = None
_is_retraining = False  # guard flag so we don't double-retrain

# Import train_models logic
if '/home/syncher/ml_model' not in sys.path:
    sys.path.append('/home/syncher/ml_model')
import train_models

def trigger_retrain(threshold: float):
    global _is_retraining
    if _is_retraining:
        return
    _is_retraining = True

    def _retrain():
        try:
            logger.info(f"Retraining ML pipelines with threshold: {threshold}")
            train_models.train_pipelines(pass_threshold=threshold)
            # Force reload next time pipelines are requested
            global _reg_pipeline, _clf_pipeline
            _reg_pipeline = None
            _clf_pipeline = None
            logger.info("ML pipelines retrained successfully.")
        except Exception as e:
            logger.error(f"Retraining failed: {e}")
        finally:
            global _is_retraining
            _is_retraining = False

    t = threading.Thread(target=_retrain)
    t.start()

# Configure Gemini Client
import os
from google import genai

api_key = os.environ.get('GEMINI_API_KEY')
client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini Client: {e}")
else:
    logger.warning("GEMINI_API_KEY not found in environment variables.")

def get_pipelines():
    global _reg_pipeline, _clf_pipeline
    if _reg_pipeline is None:
        base = settings.BASE_DIR
        _reg_pipeline = joblib.load(os.path.join(base, 'final_regression_pipeline.joblib'))
        _clf_pipeline = joblib.load(os.path.join(base, 'final_classification_pipeline.joblib'))
    return _reg_pipeline, _clf_pipeline

def predict_analysis(student_data: dict, threshold: float = 50.0) -> dict:
    reg_pipe, clf_pipe = get_pipelines()
    df = pd.DataFrame([student_data])

    # Regression model → predicted numeric score (0–100)
    predicted_score = float(reg_pipe.predict(df)[0])
    predicted_score = round(min(max(predicted_score, 0), 100), 2)

    # Classification model → probability of success & binary prediction
    clf_proba = clf_pipe.predict_proba(df)[0]
    
    # Safely extract pass probability (class 1)
    # If the model only saw one class during training, clf_proba will have length 1
    if len(clf_proba) == 2:
        pass_prob = float(clf_proba[1]) * 100
    else:
        # Check which class this single probability belongs to
        # clf_pipe.classes_ contains the labels [0] or [1] (or both)
        single_class = clf_pipe.classes_[0]
        if single_class == 1:
            pass_prob = 100.0
        else:
            pass_prob = 0.0

    clf_prediction = int(clf_pipe.predict(df)[0])  # 1 = Pass, 0 = Fail

    # Promotion decision is driven by the classification model
    # Additionally check if score is close to threshold → Reassess
    margin = 5.0
    needs_reassessment = clf_prediction == 0 and abs(predicted_score - threshold) <= margin

    if clf_prediction == 1:
        promotion_status = "Promote"
    elif needs_reassessment:
        promotion_status = "Reassess"
    else:
        promotion_status = "Repeat"

    needs_remedies = promotion_status in ("Repeat", "Reassess")

    recommendation_one_liner = "Keep up consistent study habits and maintain good attendance."
    remedy_details = []

    # ── Gemini Integration ──────────────────────────────────────────────────────
    if client:
        try:
            if needs_remedies:
                remedy_instruction = (
                    f"The student is recommended to {promotion_status}. "
                    "Provide 3 specific, practical remedies they should apply to improve."
                )
            else:
                remedy_instruction = (
                    "The student is on track to be promoted. "
                    "Provide 2 tips to maintain and further improve their performance."
                )

            prompt = f"""
            Role: Academic Performance Advisor.
            Student Data: {json.dumps(student_data)}
            Predicted Score: {predicted_score}/100
            Pass Probability: {round(pass_prob, 1)}%
            Pass Threshold: {threshold}
            Decision: {promotion_status}

            Task:
            1. Write a single professional 'one_liner' recommendation.
            2. {remedy_instruction}

            Return ONLY valid JSON:
            {{
              "one_liner": "Your text here...",
              "remedies": ["remedy 1", "remedy 2", "remedy 3"]
            }}
            """
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            text = response.text.strip()
            if text.startswith('```json'):
                text = text.replace('```json', '', 1).replace('```', '', 1).strip()
            res_json = json.loads(text)
            recommendation_one_liner = res_json.get('one_liner', recommendation_one_liner)
            remedy_details = res_json.get('remedies', [])
        except Exception as e:
            logger.error(f"Gemini API error: {e}")

    # Fallback remedies if Gemini is unavailable
    if needs_remedies and not remedy_details:
        if promotion_status == "Reassess":
            remedy_details = [
                "Schedule a reassessment with the teacher within the next two weeks.",
                "Increase weekly study hours by at least 5 hours.",
                "Seek tutoring support in the subjects where scores are lowest.",
            ]
        else:
            remedy_details = [
                "Develop a structured daily study timetable and stick to it.",
                "Improve attendance — aim for 90% or higher each term.",
                "Engage with a tutor or study group at least twice per week.",
            ]

    return {
        'score': predicted_score,
        'pass_prob': pass_prob,
        'promotion_status': promotion_status,
        'needs_remedies': needs_remedies,
        'needs_reassessment': needs_reassessment,
        'remedy_details': remedy_details,
        'one_liner': recommendation_one_liner,
        'threshold': threshold
    }

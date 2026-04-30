"""
Student Performance Prediction — Training Pipeline
Dataset : student-mat.csv  (396 Portuguese math students)
Target  : G3 final grade (0-20 regression) / Pass flag G3 >= 10 (classification)
"""

import os
import sys
import datetime
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score, f1_score, accuracy_score
from xgboost import XGBRegressor, XGBClassifier
import joblib

from analytics.ml_logic import BehavioralFeatureEngineer


# ── Logger: mirrors stdout to train_output.log ────────────────────────────────
class Tee:
    def __init__(self, log_path):
        self.terminal = sys.stdout
        self.log = open(log_path, 'a', encoding='utf-8')
        ts  = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sep = '=' * 60
        for s in (self.terminal, self.log):
            s.write(f"\n{sep}\n  TRAINING RUN  —  {ts}\n{sep}\n")
            s.flush()

    def write(self, msg):
        self.terminal.write(msg)
        self.log.write(msg)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()


# ── Column definitions ────────────────────────────────────────────────────────
# BehavioralFeatureEngineer transforms all columns to numeric representations.
NUMERIC_COLS = [
    'Hours_Studied', 'Attendance', 'Parental_Involvement', 'Access_to_Resources',
    'Extracurricular_Activities', 'Sleep_Hours', 'Previous_Scores', 'Motivation_Level',
    'Internet_Access', 'Tutoring_Sessions', 'Family_Income', 'Teacher_Quality',
    'School_Type', 'Peer_Influence', 'Physical_Activity', 'Learning_Disabilities',
    'Parental_Education_Level', 'Distance_from_Home', 'Gender',
    # Engineered
    'academic_focus', 'wellness_score', 'total_support'
]

PASS_THRESHOLD = 55   # Exam_Score >= 55 → High Performance


# ── Pipeline builder ──────────────────────────────────────────────────────────
def build_preprocessor():
    return ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), NUMERIC_COLS),
        ],
        remainder='drop',
    )


def build_pipeline(model):
    return Pipeline([
        ('engineer',  BehavioralFeatureEngineer()),
        ('preprocess', build_preprocessor()),
        ('model',     model),
    ])


# ── Main training routine ─────────────────────────────────────────────────────
def train_pipelines(pass_threshold: float = PASS_THRESHOLD):
    """Retrain pipelines using the dynamic DOS pass mark for the classification model target."""
    base     = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base, 'train_output.log')
    tee      = Tee(log_path)
    sys.stdout = tee

    try:
        csv_path = os.path.join(base, 'StudentPerformanceFactors.csv')
        print(f"Dataset  : {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"Rows     : {len(df):,}  |  Columns : {df.shape[1]}")
        print(f"Score range : {df['Exam_Score'].min()} – {df['Exam_Score'].max()}")

        # ── Targets ──────────────────────────────────────────────────────────
        df['High_Performance'] = (df['Exam_Score'] >= pass_threshold).astype(int)
        X     = df.drop(columns=['Exam_Score', 'High_Performance'])
        y_reg = df['Exam_Score']
        y_clf = df['High_Performance']
        print(f"High Performance rate : {y_clf.mean()*100:.1f}%  (threshold >= {pass_threshold})\n")

        # ── Regression ───────────────────────────────────────────────────────
        print("─" * 55)
        print("  REGRESSION  —  Exam Score Prediction")
        print("─" * 55)
        X_tr, X_te, y_tr, y_te = train_test_split(X, y_reg, test_size=0.2, random_state=42)
        reg_pipe = build_pipeline(
            XGBRegressor(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=5,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
            )
        )
        reg_pipe.fit(X_tr, y_tr)
        preds_reg = reg_pipe.predict(X_te)
        reg_mae = mean_absolute_error(y_te, preds_reg)
        reg_r2  = r2_score(y_te, preds_reg)
        print(f"  MAE           : {reg_mae:.4f}")
        print(f"  R²            : {reg_r2:.4f}\n")

        # ── Classification ────────────────────────────────────────────────────
        print("─" * 55)
        print("  CLASSIFICATION  —  High Performance Prediction")
        print("─" * 55)
        
        unique_classes = y_clf.unique()
        if len(unique_classes) == 1:
            print(f"  WARNING: Only one class present ({unique_classes[0]}). Using DummyClassifier.")
            from sklearn.dummy import DummyClassifier
            clf_pipe = build_pipeline(
                DummyClassifier(strategy='constant', constant=unique_classes[0])
            )
            clf_pipe.fit(X, y_clf)
            preds_clf = clf_pipe.predict(X)
            from sklearn.metrics import f1_score, accuracy_score
            clf_f1 = f1_score(y_clf, preds_clf, zero_division=0)
            clf_acc = accuracy_score(y_clf, preds_clf)
        else:
            X_tr_c, X_te_c, y_tr_c, y_te_c = train_test_split(X, y_clf, test_size=0.2, random_state=42)
            clf_pipe = build_pipeline(
                XGBClassifier(
                    n_estimators=200,
                    learning_rate=0.05,
                    max_depth=5,
                    random_state=42,
                    n_jobs=-1,
                    eval_metric='logloss',
                )
            )
            clf_pipe.fit(X_tr_c, y_tr_c)
            preds_clf = clf_pipe.predict(X_te_c)
            from sklearn.metrics import f1_score, accuracy_score
            clf_f1  = f1_score(y_te_c, preds_clf, zero_division=0)
            clf_acc = accuracy_score(y_te_c, preds_clf)
            
        print(f"  F1 Score      : {clf_f1:.4f}")
        print(f"  Accuracy      : {clf_acc*100:.2f}%\n")

        # ── Export ────────────────────────────────────────────────────────────
        reg_path = os.path.join(base, 'final_regression_pipeline.joblib')
        clf_path = os.path.join(base, 'final_classification_pipeline.joblib')
        joblib.dump(reg_pipe, reg_path)
        joblib.dump(clf_pipe, clf_path)

        print(f"  ✅  Pipelines exported to {base}")
        print("─" * 55)

    finally:
        sys.stdout = tee.terminal
        tee.close()
        print(f"\nLog saved → {log_path}")


if __name__ == '__main__':
    train_pipelines()

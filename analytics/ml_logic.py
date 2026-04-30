import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class BehavioralFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Custom transformer for the StudentPerformanceFactors.csv dataset.
    Handles ordinal/binary encoding, NaN imputation, and feature engineering.
    """

    BINARY_COLS = [
        'Extracurricular_Activities', 'Internet_Access', 
        'Learning_Disabilities'
    ]
    
    ORDINAL_MAPS = {
        'Parental_Involvement': {'Low': 0, 'Medium': 1, 'High': 2},
        'Access_to_Resources':  {'Low': 0, 'Medium': 1, 'High': 2},
        'Motivation_Level':    {'Low': 0, 'Medium': 1, 'High': 2},
        'Family_Income':       {'Low': 0, 'Medium': 1, 'High': 2},
        'Teacher_Quality':     {'Low': 0, 'Medium': 1, 'High': 2},
        'Distance_from_Home':  {'Near': 0, 'Moderate': 1, 'Far': 2},
        'Peer_Influence':      {'Negative': 0, 'Neutral': 1, 'Positive': 2},
        'Parental_Education_Level': {'High School': 0, 'College': 1, 'Postgraduate': 2}
    }

    def fit(self, X, y=None):
        X = X.copy()
        # Compute mode for every column
        self.modes_ = X.mode().iloc[0]
        return self

    def transform(self, X):
        X = X.copy()

        # ── 1. Impute NaN ────────────────────────────────────────────────────
        for col in X.columns:
            if col in self.modes_.index:
                X[col] = X[col].fillna(self.modes_[col])

        # ── 2. Binary Encoding ───────────────────────────────────────────────
        yes_no_map = {'Yes': 1, 'No': 0}
        for col in self.BINARY_COLS:
            if col in X.columns:
                X[col] = X[col].map(yes_no_map).fillna(0).astype(int)

        if 'Gender' in X.columns:
            X['Gender'] = X['Gender'].map({'Male': 1, 'Female': 0}).fillna(0).astype(int)
        
        if 'School_Type' in X.columns:
            X['School_Type'] = X['School_Type'].map({'Public': 1, 'Private': 0}).fillna(1).astype(int)

        # ── 3. Ordinal Encoding ──────────────────────────────────────────────
        for col, mapping in self.ORDINAL_MAPS.items():
            if col in X.columns:
                X[col] = X[col].map(mapping).fillna(0).astype(int)

        # ── 4. Engineered features ───────────────────────────────────────────
        # Academic focus: Hours Studied vs Previous Scores
        X['academic_focus'] = X['Hours_Studied'] * (X['Previous_Scores'] / 100.0)
        
        # Wellness balance: Sleep vs Physical Activity
        X['wellness_score'] = (X['Sleep_Hours'] + X['Physical_Activity']) / 2.0
        
        # Support signal: Parental Involvement + Tutoring
        X['total_support'] = X['Parental_Involvement'] + (X['Tutoring_Sessions'] > 0).astype(int)

        return X

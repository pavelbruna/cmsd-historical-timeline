#!/usr/bin/env python3
"""Test Gemini API and list available models"""

import os
import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY", "AIzaSyBPq3JFpn0pK1IcsHZY4VaTfkApy3q1ZiI")
genai.configure(api_key=api_key)

print("Available models:")
print("="*70)

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"[OK] {m.name}")
            print(f"  Display: {m.display_name}")
            print(f"  Description: {m.description[:80]}")
            print()
except Exception as e:
    print(f"Error listing models: {e}")
    print("\nTrying common model names...")

    # Try common model names
    models_to_try = [
        'gemini-1.5-flash',
        'gemini-1.5-flash-latest',
        'gemini-1.5-pro',
        'gemini-pro',
        'gemini-pro-vision',
    ]

    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            print(f"[OK] {model_name}")
        except Exception as e:
            print(f"[ERROR] {model_name} - {str(e)[:60]}")

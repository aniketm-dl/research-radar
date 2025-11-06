#!/usr/bin/env python3
"""Test script to check available Gemini models."""

import os
import google.generativeai as genai

# Load API key from CREDENTIALS.md
api_key = "AIzaSyAI4c0X19_qJSnJm4PxLOM6JowljZeZUWY"

genai.configure(api_key=api_key)

print("Available models:")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"  - {model.name}")

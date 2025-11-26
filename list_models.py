import google.generativeai as genai
import os

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("Bitte zuerst: export GEMINI_API_KEY=...")

genai.configure(api_key=api_key)

models = genai.list_models()

for m in models:
    print(m.name, " | supports: ", m.supported_generation_methods)




import os
import io
import csv
import requests
import pandas as pd
import tempfile
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from django.http import JsonResponse, FileResponse
from django.core.files.storage import default_storage
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from openai import OpenAI

# Config
OPENROUTER_API_KEY = "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"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")


# Helper: Extract text from PDF
def extract_text_from_pdf(file_obj):
    reader = PdfReader(file_obj)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

# Helper: Extract text from URL
def extract_text_from_url(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        return soup.get_text()
    except Exception as e:
        return f"Failed to fetch URL content: {str(e)}"

# Helper: Extract text from uploaded CSV
def extract_text_from_csv(file_obj):
    file_obj.seek(0)
    return file_obj.read().decode("utf-8")

def get_prompt(clean_text, test_type):
    return f"""You are a software quality assurance expert. Based on the input provided, generate **{test_type}** test cases in a pipe-separated format (|).

Do NOT categorize into subtypes like Positive, Negative, Boundary, or Edge. All scenarios should fall under the "{test_type}" category only.

Generate AT LEAST 30 relevant test cases.

Use the following columns separated by | :
No|Scenario|Description|Steps|Expected Result

Do not fill Actual Result, Status, or Comment. These will be filled manually later.

Input Text:
{clean_text}

Output Format (pipe-separated table):
No|Scenario|Description|Steps|Expected Result|Actual Result|Status|Comment
"""


@api_view(["POST"])
@permission_classes([AllowAny])
def chatbot_response(request):
    try:
        user_text = request.data.get("text")
        url = request.data.get("url")
        uploaded_file = request.FILES.get("file")
        test_type = request.data.get("test_type")

        if not test_type:
            return JsonResponse({"error": "Test type is required"}, status=400)

        if uploaded_file:
            filename = uploaded_file.name.lower()
            if filename.endswith(".pdf"):
                input_text = extract_text_from_pdf(uploaded_file)
            elif filename.endswith(".csv"):
                input_text = extract_text_from_csv(uploaded_file)
            elif filename.endswith(".txt"):
                input_text = uploaded_file.read().decode("utf-8")
            else:
                return JsonResponse({"error": "Unsupported file type"}, status=400)
        elif url:
            input_text = extract_text_from_url(url)
        elif user_text:
            input_text = user_text
        else:
            return JsonResponse({"error": "No valid input provided"}, status=400)

        prompt = get_prompt(input_text, test_type)  # ✅ Use test_type here

        # AI call
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=2048,
            top_p=0.9
        )

        generated_csv_text = response.choices[0].message.content if response.choices else ""

        if not generated_csv_text.strip():
            return JsonResponse({"error": "No test cases generated."}, status=400)

        # Remove markdown code fences
        if "```csv" in generated_csv_text:
            generated_csv_text = generated_csv_text.split("```csv")[1].split("```")[0].strip()
        elif "```" in generated_csv_text:
            generated_csv_text = generated_csv_text.split("```")[1].strip()

        # Parse CSV from pipe-separated text
        csv_input = io.StringIO(generated_csv_text)
        try:
            df = pd.read_csv(csv_input, sep='|', engine='python')
        except Exception as e:
            return JsonResponse({"error": f"CSV parsing failed: {str(e)}"}, status=500)

        if df.shape[1] < 5:
            return JsonResponse({"error": "Parsed CSV has fewer than 5 columns."}, status=500)

        # Add missing columns
        for col in ["Actual Result", "Status", "Comment"]:
            if col not in df.columns:
                df[col] = ""

        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        output_path = os.path.join(settings.MEDIA_ROOT, "test_cases.csv")
        df.to_csv(output_path, index=False)

        download_url = request.build_absolute_uri("/media/test_cases.csv")

        return JsonResponse({
            "message": "Test cases generated successfully.",
            "download_csv_url": download_url
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

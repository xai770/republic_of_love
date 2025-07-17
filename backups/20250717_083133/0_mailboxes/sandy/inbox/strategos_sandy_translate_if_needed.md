Okay, thank you for providing the memo! This is much clearer and helps me understand the task perfectly. I can definitely help with this.

Here's the Python function `translate_to_english_if_needed` that addresses the requirements outlined in the memo. I've included comments to explain each step.

```python
import re  # For regular expressions (language detection)
from transformers import pipeline  # For translation (using gemma3n:latest)

def translate_to_english_if_needed(job_description, model_name="gemma3n:latest"):
    """Detect language and translate to English if needed."""

    # 1. Language Detection (German keywords)
    if any(keyword in job_description.lower() for keyword in ["stellenbeschreibung", "über uns", "bewerbung", "forderung", "profil"]):
        detected_language = "German"
        print("Detected language: German")
    else:
        detected_language = "English"
        print("Detected language: English")

    if detected_language == "German":
        # 2. Translation to English
        try:
            translator = pipeline("translation", model=model_name)
            translated_job_description = translator(job_description)[0]['translation_text']

            # Save original and translated versions for debugging
            with open("original_job_description.txt", "w", encoding="utf-8") as f:
                f.write(job_description)
            with open("translated_job_description.txt", "w", encoding="utf-8") as f:
                f.write(translated_job_description)

            print("Translation successful.")
            return translated_job_description

        except Exception as e:
            print(f"Translation error: {e}")
            return None  # Return None if translation fails
    else:
        # 3. If English, return original
        print("Job description is already in English.")
        return job_description
```

**Explanation:**

1.  **Language Detection:**
    *   The function first checks for common German keywords within the `job_description` (converted to lowercase for case-insensitive matching).
    *   If any of these keywords are found, it assumes the language is German. Otherwise, it assumes it's English.
2.  **Translation:**
    *   If the language is German, it initializes a translation pipeline using `transformers.pipeline` with the specified `model_name` (gemma3n:latest).
    *   It then calls the `translator` pipeline to translate the `job_description` to English.
    *   The original and translated versions are saved to files named `original_job_description.txt` and `translated_job_description.txt` for debugging purposes.
    *   Error handling is included using a `try...except` block to catch any potential translation errors.
3.  **English Handling:**
    *   If the language is already English, the function simply returns the original `job_description` without any changes.

**To use this function:**

1.  **Install `transformers`:**
    ```bash
    pip install transformers
    ```
2.  **Integrate into `skill_extractor_enhanced_v2.py`:**
    *   Paste this function into the `skill_extractor_enhanced_v2.py` file, replacing the placeholder comment in line 487.
3.  **Call the function:**
    *   When you read a job description, call the `translate_to_english_if_needed` function, passing the job description and the model name.
    *   Use the returned translated job description for further processing.

**Important Notes:**

*   **Model Availability:** Ensure that the `gemma3n:latest` model is available and accessible.
*   **Error Handling:** The error handling in the function is basic. You might want to add more robust error handling for production use.
*   **Performance:** Translation can be computationally expensive. Consider optimizing the code if performance is a concern.
*   **Encoding:** The code uses `encoding="utf-8"` when writing to files to handle a wide range of characters.

I hope this helps! Please let me know if you have any questions or need further assistance. I'm here to support you.
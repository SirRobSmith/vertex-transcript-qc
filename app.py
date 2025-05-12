from flask import Flask, jsonify
from google import genai
from google.genai import types
from modules.vertex import *
import base64
from google.cloud import storage 

# Define some constants
GCP_PROJECT_ID = "ab-architecture"
GCP_LOCATION = "us-central1"

# Initialize the Flask application
app = Flask(__name__)

# Define a simple health check endpoint, mostly to see if the app is running
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200


@app.route('/generate-feedback', methods=['GET'])
def generate_feedback():

    def read_file_from_gcs(bucket_name, file_name):
        """Reads a file from a GCP bucket and returns its content."""

        try:
            # Initialize the GCP storage client
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(file_name)

            # Download the file content as bytes
            file_content = blob.download_as_bytes()
            return file_content

        except Exception as e:
            # Handle exceptions (e.g., file not found, permission issues)
            return f"Error reading file from GCP bucket: {str(e)}", 500

    def generate():
        client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT_ID,
            location=GCP_LOCATION,
        )

        # Define the GCP bucket and file name
        bucket_name = "hackfest-2025-demo"
        file_name = "chatlog.txt"

        # Read the content of chatlog.txt from the GCP bucket
        chatlog_data = read_file_from_gcs(bucket_name, file_name)
        if isinstance(chatlog_data, tuple):  # Check if an error occurred
            return chatlog_data

        # Encode the content in base64
        chatlog_data_base64 = base64.b64encode(chatlog_data).decode("utf-8")

        # Create msg3_document1 dynamically from the chatlog data
        msg3_document1 = types.Part.from_bytes(
            data=base64.b64decode(chatlog_data_base64),
            mime_type="text/plain",
        )

        model = "gemini-2.0-flash-001"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text="""Analyse these chat logs and rank the agents based on the professionalism they show in the chat log.""")
                ]
            ),
            types.Content(
                role="user",
                parts=[
                    msg3_document1,
                    types.Part.from_text(text="""analyse the records in this file""")
                ]
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            max_output_tokens=8192,
            response_modalities=["TEXT"],
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
            ],
        )

        response_text = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            response_text += chunk.text

        return response_text

    return generate(), 200


if __name__ == '__main__':
    app.run(debug=True, port=5555)







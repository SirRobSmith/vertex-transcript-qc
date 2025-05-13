from flask import Flask, jsonify
from google import genai
from google.genai import types
from modules.slack import send_to_slack
import base64
from google.cloud import storage 
import json
import re

# Define some constants
GCP_PROJECT_ID = "prj-i-big-foxhound-9f7a"
GCP_LOCATION = "us-central1"

# Define the Slack webhook URL as a constant
SLACK_WEBHOOK_URL = "https://hooks.slack.com/triggers/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"

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

    def generate(chatlog, user_prompt, documents):
        """
        Generates a response using Vertex AI based on a user prompt and documents.

        Args:
            user_prompt (str): The user's input prompt.
            documents (list): A list of document contents (as strings or bytes).

        Returns:
            str: The generated response text.
        """
        client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT_ID,
            location=GCP_LOCATION,
        )

        # Create parts for the documents
        document_parts = [
            types.Part.from_bytes(data=doc if isinstance(doc, bytes) else doc.encode("utf-8"), mime_type="text/plain")
            for doc in documents
        ]

        print(f"Document parts: {document_parts}")


        chatlog_part = types.Part.from_text(text=chatlog)

        # Construct the contents list dynamically
        contents = [

            types.Content(
                role="user",
                parts=document_parts + [
                    types.Part.from_text(text=user_prompt)
                ]
            ),
            # Add the chatlog part if it exists
            types.Content(
                role="user",
                parts=[chatlog_part]
            )
        ]

        model = "gemini-2.5-pro-preview-05-06"
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

    def process_prompts(chatlog):
        """Reads the prompts.json file and processes each category against the chatlog."""
        try:
            # Open and load the prompts.json file
            with open("prompts.json", "r") as file:
                prompts_data = json.load(file)

            # Loop through each category in the JSON file
            returned_data = []
            for category in prompts_data:

                # Print the category name (for debugging)
                print(f"Working on Category: {category['category']}")

                # Loop through each prompt in the category
                for prompt in category.get("prompts", []):

                    # Print the prompt name and text (for debugging)
                    print(f"  Prompt: {prompt['prompt']}")

                    # Define an empty list to store artefacts for this prompt
                    all_category_artefacts = []

                    # Loop through each artefact in the prompt
                    for artefact in category.get("artefacts", []):

                        # Print the artefact name and path (for debugging)
                        print(f"  Artefact Path: {artefact['path']}")

                        # Add the artefact path to the list
                        all_category_artefacts.append(artefact['path'])

                    # Print the list of artefacts for this prompt (for debugging)
                    print(f"all_category_artefacts: {all_category_artefacts}")

                    # Print an example of the call to vertex (for debugging)
                    print(f"Making a call to vertex with the prompt: {prompt['prompt']} and artefacts{all_category_artefacts}")

                    # Capture the response from vertex
                    response = generate(chatlog, prompt['prompt'], all_category_artefacts)

                    # Add it to the returned data
                    response_no_escapes = re.sub(r'\\[ntr"]', '', response)


                    returned_data.append({
                        "category": category['category'],
                        "prompt": prompt['prompt'],
                        "response": response_no_escapes
                    })

            return returned_data
            

        except FileNotFoundError:
            print("Error: prompts.json file not found.")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
        


    def process_chatlog():
        """Reads the chatlog.json file and processes each item."""
        try:
            # Open and load the chatlog.json file
            with open("chatlog.json", "r") as file:
                chatlog_data = json.load(file)
    
            # Loop through each item in the chatlog
            print(type(chatlog_data))

            # Loop through each item in the chatlog
            for item in chatlog_data:

                print(f"Processing item: {item} (for debugging)")

                # Send it to be assessed against our prompts
                returned_data = process_prompts(item)
    
        except FileNotFoundError:
            print("Error: chatlog.json file not found.")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")

        return returned_data


    return process_chatlog(), 200



if __name__ == '__main__':
    app.run(debug=True, port=5555)








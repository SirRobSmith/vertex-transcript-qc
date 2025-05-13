import requests

def send_to_slack(webhook_url, message):
    """
    Sends a message to Slack using the provided webhook URL.

    Args:
        webhook_url (str): The Slack webhook URL.
        message (str): The message to send.

    Returns:
        Response: The HTTP response from the Slack API.
    """
    payload = {
        "chat_message": message  # The message content
    }

    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()  # Raise an error for HTTP errors
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Slack: {e}")
        return None
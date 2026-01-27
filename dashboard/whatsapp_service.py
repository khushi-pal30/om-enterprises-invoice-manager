from twilio.rest import Client

def send_whatsapp_invoice(phone, balance):
    account_sid = 'YOUR_TWILIO_SID'
    auth_token = 'YOUR_TWILIO_AUTH_TOKEN'
    client = Client(account_sid, auth_token)

    client.messages.create(
        from_='whatsapp:+14155238886',
        to=f'whatsapp:+91{phone}',
        body=f"""OM ENTERPRISES
Your invoice is generated.
Pending Amount: ₹{balance}
Thank you."""
    )

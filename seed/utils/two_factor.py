
def send_token_email(email_device):
    email_device.generate_token()
    message = f"Your Token for SEED-Platform login is: {email_device.token}"

    return email_device.send_mail(message)
    

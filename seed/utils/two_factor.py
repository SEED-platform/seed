import io
import qrcode
import base64
from django_otp.plugins.otp_totp.models import TOTPDevice

def send_token_email(email_device):
    email_device.generate_token()
    message = f"Your Token for SEED-Platform login is: {email_device.token}"

    return email_device.send_mail(message)
    
def generate_qr_code(user, devices):
        totp_device = TOTPDevice.objects.create(
                user=user,
                name="default",
                confirmed=True
            )
        if totp_device:
            [device.delete() for device in devices]
        else: 
             return

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(totp_device.config_url)
        qr.make(fit=True)

        img = qr.make_image(fill="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return img_base64
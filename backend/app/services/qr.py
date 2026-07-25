import base64
from io import BytesIO

import qrcode


def generate_qr_data_url(public_identifier: str) -> str:
    """Genera un QR PNG en memoria usando solo el identificador público."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(public_identifier)
    qr.make(fit=True)

    image = qr.make_image(fill_color="#0b2f25", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded_image = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded_image}"

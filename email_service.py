import smtplib
from email.message import EmailMessage
from datetime import datetime
from email_config import SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL, SMTP_SERVER, SMTP_PORT
from menu import MENU


def get_item_price(name):
    """Safely retrieves the price of an item from MENU regardless of case or category."""
    for category in MENU.values():
        if name in category:
            return category[name]["price"]
        for item_name, data in category.items():
            if item_name.lower() == name.lower():
                return data["price"]
    return 0


def send_order_email(order_number, customer, items, total):
    """
    Sends an order confirmation email to the customer using SMTP credentials from environment variables.
    Logs clear error details on backend and returns True if sent, False otherwise.
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD or "YOUR_" in SENDER_EMAIL or "YOUR_" in SENDER_PASSWORD:
        print("[EMAIL ERROR] SMTP credentials not configured. Please set SENDER_EMAIL and SENDER_PASSWORD in environment.")
        return False

    recipient_email = customer.get("email", "").strip()
    if not recipient_email:
        print(f"[EMAIL ERROR] Missing recipient customer email for Order #{order_number}.")
        return False

    order_type = customer.get("order_type", "")
    customer_name = customer.get("name", "Valued Customer")
    phone = customer.get("phone", "N/A")
    address = customer.get("address")
    order_time_str = datetime.now().strftime("%d %B %Y, %I:%M %p")

    lines = [
        f"CAFE DELIGHT - ORDER CONFIRMATION #{order_number}",
        "=" * 45,
        "",
        f"Hello {customer_name},",
        "",
        "Thank you for ordering with Cafe Delight! Here is your order summary:",
        "",
        "CUSTOMER & ORDER DETAILS",
        "-" * 30,
        f"Order Number   : #{order_number}",
        f"Order Type     : {order_type}",
        f"Customer Name  : {customer_name}",
        f"Phone Number   : {phone}",
        f"Email Address  : {recipient_email}",
    ]

    if address:
        lines.append(f"Delivery Address: {address}")

    lines += [
        f"Order Time     : {order_time_str}",
        "",
        "ORDER ITEMS",
        "-" * 30,
    ]

    for item in items:
        name = item.get("item", "")
        qty = item.get("quantity", 1)
        unit_price = get_item_price(name)
        item_total = unit_price * qty
        lines.append(f"• {qty} x {name} - Rs. {item_total} (Rs. {unit_price} each)")

    lines += [
        "",
        "-" * 30,
        f"TOTAL AMOUNT: Rs. {total}",
        "-" * 30,
        "",
        "We are preparing your order and look forward to serving you!",
        "",
        "Warm regards,",
        "Cafe Delight Team"
    ]

    msg = EmailMessage()
    msg["Subject"] = f"Cafe Delight - Order Confirmation #{order_number}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    if RECEIVER_EMAIL and RECEIVER_EMAIL.lower() != recipient_email.lower():
        msg["Bcc"] = RECEIVER_EMAIL

    msg.set_content("\n".join(lines))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"[EMAIL SUCCESS] Order confirmation #{order_number} successfully sent to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError as exc:
        print(f"[EMAIL ERROR] SMTP Authentication failed: {exc}")
        return False
    except smtplib.SMTPConnectError as exc:
        print(f"[EMAIL ERROR] SMTP Connection failed to {SMTP_SERVER}:{SMTP_PORT}: {exc}")
        return False
    except smtplib.SMTPException as exc:
        print(f"[EMAIL ERROR] SMTP Exception occurred: {exc}")
        return False
    except Exception as exc:
        print(f"[EMAIL ERROR] Unexpected error sending email for Order #{order_number}: {exc}")
        return False
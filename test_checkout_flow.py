import json
import unittest
from unittest.mock import patch, MagicMock
from app import app, db
from models import PlacedOrder
import email_service
import email_config


class CafeDelightCheckoutTestCase(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_01_empty_cart(self):
        """Test 7: Empty cart returns appropriate message on checkout."""
        res = self.client.post("/api/chat", json={"message": "checkout"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("cart is empty", data["message"].lower())

    def test_02_existing_chatbot_questions(self):
        """Test 8: Existing chatbot questions still work properly."""
        # Menu question
        res = self.client.post("/api/chat", json={"message": "show menu"})
        self.assertIn("OUR MENU", res.get_json()["message"])

        # Item price question
        res = self.client.post("/api/chat", json={"message": "How much is Cold Coffee?"})
        self.assertIn("Cold Coffee", res.get_json()["message"])
        self.assertIn("130", res.get_json()["message"])

        # Opening hours
        res = self.client.post("/api/chat", json={"message": "What are your opening hours?"})
        self.assertIn("Opening Hours", res.get_json()["message"])

        # Veg options
        res = self.client.post("/api/chat", json={"message": "Do you have vegetarian options?"})
        self.assertIn("vegetarian", res.get_json()["message"].lower())

        # Greeting
        res = self.client.post("/api/chat", json={"message": "Hi"})
        self.assertIn("Welcome to Cafe Delight", res.get_json()["message"])

    def test_03_takeaway_checkout_flow_with_email_validation(self):
        """Test 1, 4, 5, 6: Takeaway checkout, invalid email, valid email, multiple items."""
        state = None

        # Add 2 chicken burgers (item 1)
        res = self.client.post("/api/chat", json={"message": "2 chicken burgers", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertEqual(data["cart"]["total_items"], 2)

        # Add 1 cold coffee (item 2) - multiple items
        res = self.client.post("/api/chat", json={"message": "add 1 cold coffee", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertEqual(data["cart"]["total_items"], 3)
        self.assertEqual(data["cart"]["total"], 2 * 180 + 130)  # 360 + 130 = 490

        # Start checkout
        res = self.client.post("/api/chat", json={"message": "checkout", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertIn("may I have your name", data["message"])

        # Provide name
        res = self.client.post("/api/chat", json={"message": "John Doe", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertIn("provide your phone number", data["message"])

        # Provide phone
        res = self.client.post("/api/chat", json={"message": "9876543210", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertIn("Dine-in, Takeaway, or Delivery", data["message"])

        # Select Takeaway -> should ask for email
        res = self.client.post("/api/chat", json={"message": "Takeaway", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertIn("What email address should we send your order confirmation to?", data["message"])

        # Test invalid email (Test 4)
        res = self.client.post("/api/chat", json={"message": "not-an-email", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertIn("valid email address", data["message"].lower())

        # Test another invalid email format
        res = self.client.post("/api/chat", json={"message": "user@domain", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertIn("valid email address", data["message"].lower())

        # Test valid email (Test 5)
        res = self.client.post("/api/chat", json={"message": "john.doe@example.com", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertIn("saved successfully", data["message"])
        self.assertEqual(state["customer"]["email"], "john.doe@example.com")

        # Checkout summary review
        res = self.client.post("/api/chat", json={"message": "checkout", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertIn("Email: john.doe@example.com", data["message"])
        self.assertIn("TOTAL: Rs. 490", data["message"])
        self.assertIn("Confirm Order", str(data.get("options", [])))

        # Confirm order with mocked SMTP success
        with patch("email_service.smtplib.SMTP_SSL") as mock_smtp:
            server_instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = server_instance
            with patch.object(email_service, "SENDER_EMAIL", "cafe@gmail.com"), \
                 patch.object(email_service, "SENDER_PASSWORD", "secret16passwrd"):
                res = self.client.post("/api/chat", json={"message": "confirm", "state": state})
                data = res.get_json()
                self.assertIn("ORDER CONFIRMED!", data["message"])
                self.assertIn("john.doe@example.com", data["message"])

                # Check that email was sent to customer
                server_instance.send_message.assert_called_once()
                sent_msg = server_instance.send_message.call_args[0][0]
                self.assertEqual(sent_msg["To"], "john.doe@example.com")
                self.assertIn("490", sent_msg.get_content())
                self.assertIn("Chicken Burger", sent_msg.get_content())
                self.assertIn("Cold Coffee", sent_msg.get_content())

    def test_04_delivery_checkout_flow(self):
        """Test 2: Delivery checkout flow asks for address and email, and stores them."""
        state = None

        # Add item
        res = self.client.post("/api/chat", json={"message": "1 Farmhouse Pizza", "state": state})
        state = res.get_json()["state"]

        # Checkout
        res = self.client.post("/api/chat", json={"message": "checkout", "state": state})
        state = res.get_json()["state"]

        # Name & Phone
        res = self.client.post("/api/chat", json={"message": "Alice Smith", "state": state})
        state = res.get_json()["state"]
        res = self.client.post("/api/chat", json={"message": "9123456780", "state": state})
        state = res.get_json()["state"]

        # Delivery selected -> asks address
        res = self.client.post("/api/chat", json={"message": "Delivery", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertIn("complete delivery address", data["message"])

        # Provide address -> should ask email
        res = self.client.post("/api/chat", json={"message": "42 Rosewood Lane, Floor 3", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertIn("What email address should we send your order confirmation to?", data["message"])

        # Provide email
        res = self.client.post("/api/chat", json={"message": "alice@gmail.com", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertEqual(state["customer"]["email"], "alice@gmail.com")

        # Checkout summary shows both address and email
        res = self.client.post("/api/chat", json={"message": "checkout", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertIn("Address: 42 Rosewood Lane, Floor 3", data["message"])
        self.assertIn("Email: alice@gmail.com", data["message"])

    def test_05_dine_in_checkout_flow(self):
        """Test 3: Dine-in preserves existing behavior without asking for or forcing email."""
        state = None

        # Add item
        res = self.client.post("/api/chat", json={"message": "1 Chocolate Brownie", "state": state})
        state = res.get_json()["state"]

        # Checkout
        res = self.client.post("/api/chat", json={"message": "checkout", "state": state})
        state = res.get_json()["state"]

        # Name & Phone
        res = self.client.post("/api/chat", json={"message": "David", "state": state})
        state = res.get_json()["state"]
        res = self.client.post("/api/chat", json={"message": "9876543211", "state": state})
        state = res.get_json()["state"]

        # Dine-in selected -> no email question asked!
        res = self.client.post("/api/chat", json={"message": "Dine-in", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertNotIn("What email address", data["message"])
        self.assertIn("Dine-in selected", data["message"])

        # Checkout summary
        res = self.client.post("/api/chat", json={"message": "checkout", "state": state})
        data = res.get_json()
        state = data["state"]
        self.assertIn("ORDER #", data["message"])
        self.assertIn("Type: Dine-in", data["message"])
        self.assertNotIn("Email:", data["message"])

        # Confirm order -> No email sent for dine-in
        res = self.client.post("/api/chat", json={"message": "confirm", "state": state})
        data = res.get_json()
        self.assertIn("ORDER CONFIRMED!", data["message"])
        self.assertNotIn("email notification", data["message"].lower())

    def test_06_email_service_independent(self):
        """Test 9: Test the email service independently."""
        customer = {
            "name": "Jane Doe",
            "phone": "9998887777",
            "order_type": "Delivery",
            "address": "10 Downing St",
            "email": "jane@example.com"
        }
        items = [
            {"item": "Veg Burger", "quantity": 2},
            {"item": "Fresh Lime Soda", "quantity": 1}
        ]
        total = 2 * 140 + 90

        # Unconfigured credentials should return False and log clearly
        with patch.object(email_service, "SENDER_EMAIL", ""), \
             patch.object(email_service, "SENDER_PASSWORD", ""):
            success = email_service.send_order_email(1234, customer, items, total)
            self.assertFalse(success)

        # Missing recipient email should return False
        with patch.object(email_service, "SENDER_EMAIL", "cafe@example.com"), \
             patch.object(email_service, "SENDER_PASSWORD", "pwd1234567890123"):
            bad_customer = dict(customer)
            bad_customer["email"] = ""
            success = email_service.send_order_email(1234, bad_customer, items, total)
            self.assertFalse(success)

        # Configured credentials and mocked SMTP success
        with patch.object(email_service, "SENDER_EMAIL", "cafe@example.com"), \
             patch.object(email_service, "SENDER_PASSWORD", "pwd1234567890123"), \
             patch("email_service.smtplib.SMTP_SSL") as mock_smtp:
            server_mock = MagicMock()
            mock_smtp.return_value.__enter__.return_value = server_mock
            success = email_service.send_order_email(1234, customer, items, total)
            self.assertTrue(success)
            server_mock.login.assert_called_with("cafe@example.com", "pwd1234567890123")
            server_mock.send_message.assert_called_once()
            msg = server_mock.send_message.call_args[0][0]
            self.assertEqual(msg["To"], "jane@example.com")
            self.assertIn("Veg Burger", msg.get_content())
            self.assertIn("Fresh Lime Soda", msg.get_content())
            self.assertIn("10 Downing St", msg.get_content())

    def test_07_no_secrets_in_codebase(self):
        """Test 10: Ensure no hardcoded SMTP passwords or sensitive secrets in Python code."""
        with open("email_config.py", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertNotIn("yxaysuytcdvvzsom", content)
            self.assertNotIn("anantmann157", content)
            self.assertNotIn("kgaganjot08", content)

        with open(".gitignore", "r", encoding="utf-8") as f:
            gitignore = f.read()
            self.assertIn(".env*", gitignore)

    def test_08_cart_apis(self):
        """Ensure existing cart APIs (view, clear, summary) continue working."""
        # Add item
        res = self.client.post("/api/chat", json={"message": "1 Veg Burger"})
        state = res.get_json()["state"]

        # View cart API
        res = self.client.post("/api/cart/view", json={"state": state})
        self.assertEqual(res.status_code, 200)
        self.assertIn("Veg Burger", res.get_json()["message"])

        # Cart summary API
        res = self.client.get("/api/cart/summary")
        self.assertEqual(res.status_code, 200)

        # Clear cart API
        res = self.client.post("/api/cart/clear", json={"state": state})
        self.assertEqual(res.status_code, 200)
        self.assertIn("cleared", res.get_json()["message"].lower())

    def test_09_price_limit_queries(self):
        """Test user queries asking for items under a specific price."""
        # 1. "Show me something under ₹100"
        res = self.client.post("/api/chat", json={"message": "Show me something under ₹100"})
        msg = res.get_json()["message"]
        self.assertIn("Fresh Lime Soda", msg)
        self.assertIn("90", msg)

        # 2. "What can I get below ₹50?" (below minimum price)
        res = self.client.post("/api/chat", json={"message": "What can I get below ₹50?"})
        msg = res.get_json()["message"]
        self.assertIn("don't currently have any items under ₹50", msg)
        self.assertIn("starts from Rs. 90", msg)
        self.assertIn("Fresh Lime Soda", msg)

        # 3. "Food under 200"
        res = self.client.post("/api/chat", json={"message": "Food under 200"})
        msg = res.get_json()["message"]
        self.assertIn("Fresh Lime Soda", msg)
        self.assertIn("Veg Burger", msg)
        self.assertIn("Cheese Burger", msg)
        self.assertNotIn("Margherita Pizza", msg)  # Pizza is 220 > 200

        # 4. "Show me burgers under ₹150" (category + price filter)
        res = self.client.post("/api/chat", json={"message": "Show me burgers under ₹150"})
        msg = res.get_json()["message"]
        self.assertIn("Veg Burger", msg)
        self.assertIn("140", msg)
        self.assertNotIn("Cheese Burger", msg)  # 160 > 150
        self.assertNotIn("Chicken Burger", msg)  # 180 > 150
        self.assertNotIn("Fresh Lime Soda", msg)  # Not a burger

        # 5. "Anything less than ₹1?"
        res = self.client.post("/api/chat", json={"message": "Anything less than ₹1?"})
        msg = res.get_json()["message"]
        self.assertIn("don't currently have any items under ₹1", msg)
        self.assertIn("starts from Rs. 90", msg)

        # 6. Additional natural variations:
        res = self.client.post("/api/chat", json={"message": "What can I buy for 50?"})
        self.assertIn("don't currently have any items under ₹50", res.get_json()["message"])

        res = self.client.post("/api/chat", json={"message": "Give me something below Rs 80"})
        self.assertIn("don't currently have any items under ₹80", res.get_json()["message"])

        res = self.client.post("/api/chat", json={"message": "Do you have anything under 100 rs?"})
        self.assertIn("Fresh Lime Soda", res.get_json()["message"])

    def test_10_cheapest_item_queries(self):
        """Test user queries asking for the cheapest item."""
        # Overall cheapest item
        res = self.client.post("/api/chat", json={"message": "What's the cheapest item?"})
        msg = res.get_json()["message"]
        self.assertIn("cheapest item", msg.lower())
        self.assertIn("Fresh Lime Soda", msg)
        self.assertIn("90", msg)

        # Category cheapest item
        res = self.client.post("/api/chat", json={"message": "What is the cheapest burger?"})
        msg = res.get_json()["message"]
        self.assertIn("Veg Burger", msg)
        self.assertIn("140", msg)

    def test_11_preserved_existing_queries(self):
        """Ensure standard queries do not get mistakenly parsed as price queries."""
        # Opening hours
        res = self.client.post("/api/chat", json={"message": "What are your opening hours?"})
        self.assertIn("Opening Hours", res.get_json()["message"])

        # Show me burgers
        res = self.client.post("/api/chat", json={"message": "Show me burgers"})
        msg = res.get_json()["message"]
        self.assertIn("Veg Burger", msg)
        self.assertIn("Cheese Burger", msg)
        self.assertIn("Chicken Burger", msg)

        # Order chicken burgers with quantity
        res = self.client.post("/api/chat", json={"message": "2 chicken burgers"})
        data = res.get_json()
        self.assertEqual(data["cart"]["total_items"], 2)

        # How much is the pizza?
        res = self.client.post("/api/chat", json={"message": "How much is the Margherita Pizza?"})
        self.assertIn("220", res.get_json()["message"])


if __name__ == "__main__":
    unittest.main()



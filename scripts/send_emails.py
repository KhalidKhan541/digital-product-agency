#!/usr/bin/env python3
"""Send emails using Gmail SMTP"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_email(to_email, to_name, subject, body):
    """Send email via Gmail SMTP"""
    
    sender = os.environ.get("SENDER_EMAIL", "khalid.khan46571@gmail.com")
    password = os.environ.get("GMAIL_APP_PASSWORD", "YOUR_APP_PASSWORD")
    
    msg = MIMEMultipart()
    msg["From"] = f"Digital Product Agency <{sender}>"
    msg["To"] = f"{to_name} <{to_email}>"
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send: {e}")
        return False


def send_launch_sequence(to_email, to_name, product_name):
    """Send 5-email launch sequence"""
    
    emails = [
        {
            "subject": f"Your {product_name} is ready!",
            "body": f"Hi {to_name},\n\nGreat news! Your digital product '{product_name}' has been created and is ready for launch.\n\nI've prepared:\n- Complete product content\n- Landing page copy\n- Email launch sequence\n\nLet's schedule a call to discuss the launch strategy.\n\nBest regards"
        },
        {
            "subject": f"Here's what {product_name} will do for your audience",
            "body": f"Hi {to_name},\n\nI wanted to share how '{product_name}' will help your audience:\n\n1. Solve their biggest problem\n2. Provide actionable steps\n3. Deliver results quickly\n\nYour audience will love this.\n\nReady to launch?"
        },
        {
            "subject": "Success story from a similar creator",
            "body": f"Hi {to_name},\n\nA creator similar to you launched a product last month.\n\nResults:\n- 500 sales in first week\n- $5,000 revenue\n- 95% positive feedback\n\nYour product '{product_name}' can do the same.\n\nLet's make it happen."
        },
        {
            "subject": f"Last 2 days to launch {product_name}",
            "body": f"Hi {to_name},\n\nJust a reminder - we're ready to launch '{product_name}' whenever you give the green light.\n\nThe longer we wait, the more your audience misses out.\n\nWhat do you say?"
        },
        {
            "subject": f"Final chance - {product_name} launch",
            "body": f"Hi {to_name},\n\nThis is my final message about '{product_name}'.\n\nI believe this product will help your audience and generate great revenue for both of us.\n\nIf you're interested, reply YES and we'll launch this week.\n\nIf not, no hard feelings. Best of luck!"
        }
    ]
    
    for i, email in enumerate(emails, 1):
        print(f"Sending email {i}/5...")
        send_email(to_email, to_name, email["subject"], email["body"])


if __name__ == "__main__":
    email = input("Recipient email: ")
    name = input("Recipient name: ")
    product = input("Product name: ")
    
    send_launch_sequence(email, name, product)

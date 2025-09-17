import os
import random
import string
import smtplib
import csv
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'Fusionxgarba@gmail.com'  # Your Gmail address
app.config['MAIL_PASSWORD'] = 'qbgw zrvn obma dcmg'  # Your Gmail app password
ADMIN_EMAIL = 'fusionxgarba@gmail.com'

TICKET_PRICES = {
    "Female Stag": 249,
    "Male Stag": 299,
    "Couple Pass": 449,
    "Group of 6": 1399
}

def generate_ticket_code():
    return f"FXG2025-{''.join(random.choices(string.digits, k=6))}"

def send_email(to_addr, subject, body, attachment_path=None):
    from_addr = app.config['MAIL_USERNAME']
    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    if attachment_path:
        attachment = open(attachment_path, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(attachment_path)}")
        msg.attach(part)

    try:
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(from_addr, app.config['MAIL_PASSWORD'])
        text = msg.as_string()
        server.sendmail(from_addr, to_addr, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Email failed to send: {e}")
        return False

@app.route('/')
def index():
    return render_template('index.html', ticket_prices=TICKET_PRICES)

@app.route('/register', methods=['POST'])
def register():
    full_name = request.form['full_name']
    phone_number = request.form['phone_number']
    email = request.form['email']
    payment_proof = request.files['payment_proof']

    # Collect ticket quantities and calculate total price
    selected_tickets = {}
    total_price = 0
    ticket_details_for_csv = []
    ticket_details_for_email = []

    for ticket_type, price in TICKET_PRICES.items():
        # Form field name will be like 'quantity_Female_Stag'
        form_field_name = f"quantity_{ticket_type.replace(' ', '_')}"
        quantity = int(request.form.get(form_field_name, 0))
        
        if quantity > 0:
            selected_tickets[ticket_type] = quantity
            total_price += quantity * price
            ticket_details_for_csv.append(f"{ticket_type}({quantity})")
            ticket_details_for_email.append(f"<li>{ticket_type}: {quantity} x ₹{price} = ₹{quantity * price}</li>")

    if not selected_tickets:
        flash('Please select at least one ticket!', 'danger')
        return redirect(url_for('index'))

    if not all([full_name, phone_number, email, payment_proof]):
        flash('All fields are required!', 'danger')
        return redirect(url_for('index'))

    if payment_proof:
        filename = secure_filename(payment_proof.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        payment_proof.save(filepath)

    ticket_code = generate_ticket_code()

    # Save to CSV
    with open('registrations.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        if os.stat('registrations.csv').st_size == 0:
            writer.writerow(['FullName', 'PhoneNumber', 'Email', 'Tickets', 'TotalPrice', 'TicketCode', 'PaymentProof'])
        writer.writerow([full_name, phone_number, email, ", ".join(ticket_details_for_csv), total_price, ticket_code, filename])

    # Send confirmation email to customer
    customer_body = f"""
    <h3>Hi {full_name},</h3>
    <p>Thank you for registering for FusionX Garba Night!</p>
    <p><b>Your Ticket Code:</b> {ticket_code}</p>
    <p><b>Ticket Details:</b></p>
    <ul>
        {''.join(ticket_details_for_email)}
    </ul>
    <p><b>Total Price:</b> ₹{total_price}</p>
    <hr>
    <h4>Event Details:</h4>
    <p><b>Date & Time:</b> Saturday, 27th September, 6 PM</p>
    <p><b>Venue:</b> Bouncers Turf, Paithan Road, Chhatrapati Sambhajinagar, Aurangabad</p>
    <p><b>Organisers Contact:</b> 9322609066, 9209283490</p>
    """
    send_email(email, "Your FusionX Garba Night Ticket!", customer_body)

    # Send notification email to admin
    admin_body = f"""
    <h3>New Registration for FusionX Garba Night!</h3>
    <p><b>Name:</b> {full_name}</p>
    <p><b>Phone:</b> {phone_number}</p>
    <p><b>Email:</b> {email}</p>
    <p><b>Ticket Details:</b></p>
    <ul>
        {''.join(ticket_details_for_email)}
    </ul>
    <p><b>Total Price:</b> ₹{total_price}</p>
    <p><b>Ticket Code:</b> {ticket_code}</p>
    """
    send_email(ADMIN_EMAIL, "New Garba Night Registration", admin_body, attachment_path=filepath)

    return redirect(url_for('success', ticket_code=ticket_code))

@app.route('/success')
def success():
    ticket_code = request.args.get('ticket_code')
    return render_template('success.html', ticket_code=ticket_code)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
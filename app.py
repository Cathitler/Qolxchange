import bcrypt  # Install bcrypt via pip
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import random
import json

from flask import Flask, render_template, request, redirect, url_for, session, flash
import bcrypt
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Admin credentials (hardcoded for automatic login)
admin_username = "Admin"
admin_password = "M8cfwKFxxw"

# Stronger admin credentials with hashed key
admin_accounts = {
    admin_username: bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())  # Automatically hash the password
}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        if username in admin_accounts and bcrypt.checkpw(password, admin_accounts[username]):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        flash("Invalid credentials", "danger")
        return redirect(url_for('login'))

    return render_template('login.html')

    
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')


        flash("Registration successful", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


TRANSACTIONS_FILE = "transactions.json"


def read_transactions():
    if os.path.exists(TRANSACTIONS_FILE):
        with open(TRANSACTIONS_FILE, "r") as file:
            return json.load(file)
    return []

def save_transactions(transactions):
    with open(TRANSACTIONS_FILE, "w") as file:
        json.dump(transactions, file, indent=4)

def generate_transaction_id():
    return f"TID-{random.randint(1000, 99999999999999999)}"


def mask_user_account(account):
    length = len(account)
    if length > 4:
        # Mask the middle part while showing the first 2 and last 2 characters
        return account[:2] + '*' * (length - 4) + account[-2:]
    return '*' * length  # If account length is 4 or less, mask the whole account

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    transactions = read_transactions()  # 
    operator_status = session.get('operator_status', 'online')  
    return render_template('index.html', transactions=transactions, operator_status=operator_status)


@app.route('/exchange', methods=['GET', 'POST'])
def exchange():
    admin_accounts = {
        "USDT TRX": "TV2Rqo9H1bhqAte4VNmcNZpfhyfi5z8tJL",
        "Payeer USD": "P1126828655",
        "EVC USD": "613678628"
    }

    if request.method == 'POST':
        send_from = request.form['send_from']
        send_to = request.form['send_to']
        amount = request.form['amount']
        user_account = request.form['user_account']

        # Get the correct admin payment info based on 'send_from'
        admin_account = admin_accounts.get(send_from, "Unknown Account")

        transaction_id = generate_transaction_id()
        transaction = {
            "id": transaction_id,
            "send_from": send_from,
            "send_to": send_to,
            "amount": amount,
            "user_account": user_account,
            "status": "pending",
            "method": f"{send_from} to {send_to}",
            "admin_account": admin_account  # Set correct admin account
        }

        # Save transaction
        transactions = read_transactions()
        transactions.append(transaction)
        save_transactions(transactions)

        # Redirect to confirmation page
        return render_template('confirmation.html', **transaction)

    return render_template('exchange.html')


@app.route('/search', methods=['GET', 'POST'])
def search_transaction():
    if request.method == 'POST':
        transaction_id = request.form['transaction_id']
        transactions = read_transactions()
        transaction = next((t for t in transactions if t['id'] == transaction_id), None)

        if transaction:
            transaction['user'] = mask_user_account(transaction['user_account'])
            return render_template('search_result.html', transaction=transaction)

        return render_template('search_result.html', message="Transaction not found.")

    return render_template('search.html')

@app.route('/confirm/<transaction_id>', methods=['GET'])
def confirm_transaction(transaction_id):
    transactions = read_transactions()
    transaction = next((t for t in transactions if t['id'] == transaction_id), None)

    if transaction:
        
        transaction['status'] = "pending"
        save_transactions(transactions)
        return render_template(
    "success.html",
    message=f"Transaction {transaction_id} has been confirmed successfully!",
    transaction_id=transaction['id'],  # Assuming 'id' is the transaction ID
    amount=transaction['amount'],
    send_from=transaction['send_from'],
    send_to=transaction['send_to'],
    user_account=transaction['user_account'],
    admin_account=transaction['admin_account']
)


    return render_template("error.html", message="Transaction not found.")

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    # Ensure admin is logged in
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    transactions = read_transactions()
    operator_status = session.get('operator_status', 'offline')
    return render_template('admin_panel.html', transactions=transactions, operator_status=operator_status)

@app.route('/admin/edit_transaction/<transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    # Ensure admin is logged in
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    transactions = read_transactions()
    transaction = next((t for t in transactions if t['id'] == transaction_id), None)

    if not transaction:
        flash("Transaction not found", "danger")
        return redirect(url_for('admin_panel'))

    if request.method == 'POST':
        # Update status based on form input
        new_status = request.form['status']
        transaction['status'] = new_status
        save_transactions(transactions)
        flash(f"Transaction {transaction_id} status updated to {new_status}", "success")
        return redirect(url_for('admin_panel'))

    return render_template('edit_transaction.html', transaction=transaction)

@app.route('/admin/delete_transaction/<transaction_id>', methods=['GET'])
def delete_transaction(transaction_id):
    # Ensure admin is logged in
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    transactions = read_transactions()
    transaction = next((t for t in transactions if t['id'] == transaction_id), None)

    if transaction:
        transactions.remove(transaction)
        save_transactions(transactions)
        flash(f"Transaction {transaction_id} deleted successfully", "success")
    else:
        flash("Transaction not found", "danger")

    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    # Logout the admin
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))  # Make sure it's 'login', not 'register'

@app.route('/admin/toggle_operator_status', methods=['POST'])
def toggle_operator_status():
    # Toggle operator status between online and offline
    current_status = session.get('operator_status', 'online')  # Default is 'online'
    new_status = 'offline' if current_status == 'online' else 'online'
    session['operator_status'] = new_status  # Save the new status to the session
    flash(f"Operator status updated to {new_status.capitalize()}", "success")
    return redirect(url_for('admin_panel'))


if __name__ == '__main__':
    app.run(debug=True)

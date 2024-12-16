import fdb
from flask import Flask, request,jsonify, render_template, redirect, url_for
import os

app = Flask(__name__)


login = ""

variable = True

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'Database', 'delivery.fdb')
    return fdb.connect(
        dsn=db_path,
        user='SYSDBA',
        password='MASTERKEY'
    )


@app.route ('/', methods = ['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/action1', methods=['POST'])
def action1():
    global variable 
    variable = True
    return render_template('login.html')

@app.route('/action2', methods=['GET','POST'])
def action2():
    global variable
    variable = False
    return render_template('login.html')

@app.route('/action3', methods=['GET', 'POST'])
def action3():
    return render_template('register.html')

@app.route('/logowanie', methods=['GET', 'POST'])
def input_text():
    global stored_text
    if request.method == 'POST':
        # Pobieramy tekst z formularza i zapisujemy go w zmiennej
        stored_text = request.form['user-input']
        if (variable):
            if (login_check(stored_text)):
                return redirect(url_for('index'))
            else:
                error_message = "Podany e-mail nie istnieje w bazie danych."
                return render_template('register.html', error_message=error_message)
        else:
            if (customer_check(stored_text)):
                '''
                email = stored_text
                conn = get_db_connection()
                cursor = conn.cursor()
                query = """
                SELECT p.*
                FROM Przesylki p
                JOIN Odbiorca o ON p.ID_Odbiorcy = o.ID_Odbiorcy
                WHERE o.EMAIL = ?
                """
                cursor.execute(query, (email,))
                results = cursor.fetchall()
                for row in results:
                    print(row)
                conn.close()'''
                return redirect(url_for('parcels', email=stored_text))
            else:
                error_message = "Brak przesyłek przypisanych do adresu"
                return render_template('index.html',error_message=error_message)
            
    return render_template('login.html')

@app.route('/parcels', methods=['GET'])
def parcels():
    email = request.args.get('email')  # Pobierz e-mail przekazany w URL
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    SELECT p.*
    FROM Przesylki p
    JOIN Odbiorca o ON p.ID_Odbiorcy = o.ID_Odbiorcy
    WHERE o.EMAIL = ?
    """
    cursor.execute(query, (email,))
    results = cursor.fetchall()
    conn.close()
    return render_template('parcels.html', email=email, parcels=results)


def login_check(text):
    conn = get_db_connection()
    cursor = conn.cursor()
    data = text
    cursor.execute("SELECT EMAIL FROM Nadawca")
    emails = cursor.fetchall()
    conn.close()

    if any(data in email for email in emails):
        return True
    else:
        return False
    
def customer_check(text): #jan.kowalski@example.com firma5@example.com
    conn = get_db_connection()
    cursor = conn.cursor()
    data = text
    cursor.execute("SELECT EMAIL FROM Odbiorca")
    emails = cursor.fetchall()
    conn.close()
    array =[]
    if any(data in email for email in emails):
        return True
    else:
        return False
    
    

    
if __name__=='__main__':
    app.run(debug=True)
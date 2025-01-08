import fdb
from flask import Flask, request,jsonify, render_template, redirect, url_for
import os
import random
from datetime import datetime

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
    #int(id_sender_find("firma1@przyklad.com"))
    return render_template('register.html')

@app.route ('/send', methods = ['GET', 'POST'])
def send():
    return render_template('send.html')

@app.route('/register', methods=['POST'])
def register_sender():
    email = request.form['email']
    phone = request.form['phone']
    user_type = request.form['user-type']  
    name = request.form['name']
    nip = request.form.get('nip', None)  
    surname = request.form.get('surname', None) 
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            EXECUTE PROCEDURE DodajNadawce (
                ?, ?, ?, ?, ?, ?, ?
            )
        """, (email, phone, 'firma' if user_type == 'company' else 'osoba_prywatna', 
              name, nip, name if user_type == 'private' else None, surname))
        
        conn.commit()
        message = "Nadawca został pomyślnie zarejestrowany!"
    except Exception as e:
        conn.rollback()  # W razie błędu cofnij transakcję
        message = f"Wystąpił błąd: {e}"
    finally:
        conn.close()

    return render_template('register.html', success_message=message)

@app.route('/add_package', methods=['POST'])
def add_package():
    global stored_text
    data = request.form
    current_date = datetime.now().strftime('%Y-%m-%d')
    employee_id = random.randint(1, 15)
    id_send = id_sender_find(stored_text)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Dodanie przesyłki i pobranie ID_PRZESYLKI
        cursor.execute("""
            EXECUTE PROCEDURE DodajPrzesylkeOdbiorceAdres (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            str(data['p_email']),
            int(data['p_nr_tel']),
            str(data['p_nazwa']),
            str(data['p_nazwisko']),
            str(data['p_nip']),
            str(data['p_ulica']),
            str(data['p_nr_budynku']),
            str(data['p_nr_mieszkania']),
            str(data['p_miasto']),
            str(data['p_kod_pocztowy']),
            str(data['p_kraj']),
            int(data['p_waga']),
            current_date,
            None,
            employee_id,
            id_send
        ))
        cursor.execute("SELECT MAX(ID_PRZESYLKI) FROM PRZESYLKI")
        id_przesylki = cursor.fetchone()[0]

        # Obsługa checkboxów z opisem
        if 'p_opis[]' in data:
            selected_options = data.getlist('p_opis[]')

            # Dodanie "Inne" z niestandardowym tekstem, jeśli wybrano
            if 'inne' in selected_options and 'other_text' in data and data['other_text']:
                selected_options.remove('inne')
                selected_options.append(data['other_text'])

            # Dodanie rekordów do tabeli Zlecenia_specjalne
            for option in selected_options:
                cursor.execute("""
                    INSERT INTO Zlecenia_specjalne (ID_PRZESYLKI, RODZAJ)
                    VALUES (?, ?)
                """, (id_przesylki, option))

        conn.commit()
        message = "Przesyłka została pomyślnie dodana wraz z opcjami specjalnymi!"
    except Exception as e:
        conn.rollback()
        message = f"Błąd: {e}"
    finally:
        conn.close()

    return render_template('confirmation.html', message=message)



@app.route('/logowanie', methods=['GET', 'POST'])
def input_text():
    global stored_text
    if request.method == 'POST':
        # Pobieramy tekst z formularza i zapisujemy go w zmiennej
        stored_text = request.form['user-input']
        if (variable):
            if (login_check(stored_text)):
                return redirect(url_for('send'))
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
    SELECT 
        p.ID_PRZESYLKI, 
        p.WAGA, 
        p.DATA_NADANIA, 
        p.DATA_DOSTARCZENIA, 
        zs.RODZAJ
    FROM 
        PRZESYLKI p
    LEFT JOIN 
        ZLECENIA_SPECJALNE zs ON p.ID_PRZESYLKI = zs.ID_PRZESYLKI
    JOIN 
        ODBIORCA o ON p.ID_ODBIORCY = o.ID_ODBIORCY
    WHERE 
        o.EMAIL = ?
    ORDER BY 
        p.ID_PRZESYLKI
    """
    cursor.execute(query, (email,))
    results = cursor.fetchall()
    conn.close()
    
    # Grupa danych przesyłek z ich zleceniami specjalnymi
    parcels = {}
    for row in results:
        parcel_id = row[0]
        if parcel_id not in parcels:
            parcels[parcel_id] = {
                "id": row[0],
                "waga": row[1],
                "data_nadania": row[2],
                "data_dostarczenia": row[3],
                "zlecenia_specjalne": []
            }
        if row[4]:
            parcels[parcel_id]["zlecenia_specjalne"].append(row[4])
    
    return render_template('parcels.html', email=email, parcels=list(parcels.values()))

def id_sender_find(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Zapytanie do bazy danych w celu pobrania ID nadawcy dla podanego emaila
        cursor.execute("SELECT ID_NADAWCY FROM Nadawca WHERE EMAIL = ? ROWS 1", (email,))
        result = cursor.fetchone()  # Pobierz pierwszy wynik
    finally:
        conn.close()
    
    if result:
        print(result)
        return int(result[0])
    else:
        return None

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
    
def customer_check(text): 
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
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
        password='MASTERKEY',
        charset='UTF8'
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

@app.route('/admin_panel', methods=['GET'])
def admin_panel():
    # Możesz dodać logikę wyświetlania panelu administratora
    return render_template('admin_panel.html')


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

        # Dodanie ubezpieczenia, jeśli wybrane
        if 'p_insurance' in data and data['p_insurance'] == '1':
            insurance_amount = int(data.get('p_insurance_amount', 0))
            if insurance_amount > 0:
                cursor.execute("""
                    INSERT INTO Ubezpieczenie (KWOTA, ID_PRZESYLKI)
                    VALUES (?, ?)
                """, (insurance_amount, id_przesylki))

        # Obsługa checkboxów z opisem
        if 'p_opis[]' in data:
            selected_options = data.getlist('p_opis[]')

            if 'inne' in selected_options and 'other_text' in data and data['other_text']:
                selected_options.remove('inne')
                selected_options.append(data['other_text'])

            for option in selected_options:
                cursor.execute("""
                    INSERT INTO Zlecenia_specjalne (ID_PRZESYLKI, RODZAJ)
                    VALUES (?, ?)
                """, (id_przesylki, option))

        conn.commit()
        message = "Przesyłka została pomyślnie dodana wraz z opcjami specjalnymi i ubezpieczeniem!"
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
        zs.RODZAJ,
        u.KWOTA
    FROM 
        PRZESYLKI p
    LEFT JOIN 
        ZLECENIA_SPECJALNE zs ON p.ID_PRZESYLKI = zs.ID_PRZESYLKI
    LEFT JOIN 
        UBEZPIECZENIE u ON p.ID_PRZESYLKI = u.ID_PRZESYLKI
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
                "zlecenia_specjalne": [],
                "kwota_ubezpieczenia": row[5]  # Kwota ubezpieczenia
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
    
@app.route('/raport_przesylek', methods=['GET'])
def raport_przesylek():
    rok = request.args.get('rok', type=int)
    
    if not rok:
        return jsonify({"error": "Musisz podać parametr 'rok'"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Liczba przesyłek wysłanych w każdym tygodniu
        cursor.execute("""
            SELECT 
                EXTRACT(WEEK FROM DATA_NADANIA) AS tydzien,
                COUNT(*) AS wszystkie_przesylki
            FROM Przesylki
            WHERE EXTRACT(YEAR FROM DATA_NADANIA) = ?
            GROUP BY EXTRACT(WEEK FROM DATA_NADANIA)
            ORDER BY tydzien
        """, (rok,))
        przesylki_tygodnie = cursor.fetchall()

        tygodnie = {int(row[0]): row[1] for row in przesylki_tygodnie}

        # 2. Liczba przesyłek do miast w każdym tygodniu
        cursor.execute("""
            SELECT 
                EXTRACT(WEEK FROM p.DATA_NADANIA) AS tydzien,
                a.MIASTO, 
                COUNT(*) AS liczba_przesylek
            FROM Przesylki p
            JOIN Adres a ON p.ID_ODBIORCY = a.ID_ADRESU
            WHERE EXTRACT(YEAR FROM p.DATA_NADANIA) = ?
            GROUP BY EXTRACT(WEEK FROM p.DATA_NADANIA), a.MIASTO
            ORDER BY tydzien, liczba_przesylek DESC
        """, (rok,))
        przesylki_do_miast = cursor.fetchall()

        miasta_tygodnie = {}
        for row in przesylki_do_miast:
            tydzien = int(row[0])
            miasto = row[1]
            liczba = row[2]
            if tydzien not in miasta_tygodnie:
                miasta_tygodnie[tydzien] = []
            miasta_tygodnie[tydzien].append({"miasto": miasto, "liczba_przesylek": liczba})

        # 3. Procent ubezpieczonych przesyłek w każdym tygodniu
        cursor.execute("""
            SELECT 
                EXTRACT(WEEK FROM p.DATA_NADANIA) AS tydzien,
                COUNT(*) AS wszystkie_przesylki,
                COUNT(u.ID_UBEZPIECZENIA) AS ubezpieczone_przesylki
            FROM Przesylki p
            LEFT JOIN Ubezpieczenie u ON p.ID_PRZESYLKI = u.ID_PRZESYLKI
            WHERE EXTRACT(YEAR FROM p.DATA_NADANIA) = ?
            GROUP BY EXTRACT(WEEK FROM p.DATA_NADANIA)
            ORDER BY tydzien
        """, (rok,))
        ubezpieczone_tygodnie = cursor.fetchall()

        procent_ubezpieczonych = {}
        for row in ubezpieczone_tygodnie:
            tydzien = int(row[0])
            wszystkie = row[1]
            ubezpieczone = row[2]
            procent = (ubezpieczone * 100.0 / wszystkie) if wszystkie > 0 else 0
            procent_ubezpieczonych[tydzien] = round(procent, 2)

    finally:
        conn.close()

    # Tworzenie raportu dla każdego tygodnia
    raport = []
    for tydzien in sorted(tygodnie.keys()):
        raport.append({
            "tydzien": tydzien,
            "wszystkie_przesylki": tygodnie[tydzien],
            "przesylki_do_miast": miasta_tygodnie.get(tydzien, []),
            "procent_ubezpieczonych": procent_ubezpieczonych.get(tydzien, 0.0)
        })

    return render_template('raport_przesylek.html', rok=rok, raporty=raport)

@app.route('/raport_uzytkownikow', methods=['GET'])
def raport_uzytkownikow():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Liczba nadawców
        cursor.execute("SELECT COUNT(*) FROM Nadawca")
        liczba_nadawcow = cursor.fetchone()[0]

        # Liczba unikalnych odbiorców
        cursor.execute("SELECT COUNT(*) FROM Odbiorca")
        liczba_odbiorcow = cursor.fetchone()[0]

        # Liczba nadawców - firmy
        cursor.execute("""
            SELECT COUNT(*)
            FROM Nadawca
            WHERE ID_NADAWCY IN (SELECT ID_NADAWCY FROM Firma)
        """)
        liczba_nadawcow_firm = cursor.fetchone()[0]

        # Liczba nadawców - osoby prywatne
        cursor.execute("""
            SELECT COUNT(*)
            FROM Nadawca
            WHERE ID_NADAWCY IN (SELECT ID_NADAWCY FROM Osoba_prywatna)
        """)
        liczba_nadawcow_prywatnych = cursor.fetchone()[0]

        # Najbardziej aktywny nadawca
        cursor.execute("""
            SELECT ID_NADAWCY, COUNT(*) AS LiczbaPrzesylek
            FROM Przesylki
            GROUP BY ID_NADAWCY
            ORDER BY LiczbaPrzesylek DESC
            FETCH FIRST 1 ROWS ONLY
        """)
        najbardziej_aktywny_nadawca = cursor.fetchone()
        if not najbardziej_aktywny_nadawca:
            najbardziej_aktywny_nadawca = (None, 0)

        # Średnia liczba przesyłek na nadawcę
        cursor.execute("""
            SELECT AVG(LiczbaPrzesylek) AS SredniaPrzesylekNaNadawce
            FROM (
                SELECT COUNT(*) AS LiczbaPrzesylek
                FROM Przesylki
                GROUP BY ID_NADAWCY
            ) AS Subquery
        """)
        srednia_przesylek_na_nadawce = cursor.fetchone()[0]
        if srednia_przesylek_na_nadawce is None:
            srednia_przesylek_na_nadawce = 0

    finally:
        conn.close()

    # Generowanie raportu
    raport = {
        "liczba_nadawcow": liczba_nadawcow,
        "liczba_odbiorcow": liczba_odbiorcow,
        "liczba_nadawcow_firm": liczba_nadawcow_firm,
        "liczba_nadawcow_prywatnych": liczba_nadawcow_prywatnych,
        "najbardziej_aktywny_nadawca": najbardziej_aktywny_nadawca,
        "srednia_przesylek_na_nadawce": srednia_przesylek_na_nadawce,
    }

    return render_template('raport_uzytkownikow.html', raport=raport)



@app.route('/raport_pracownikow', methods=['GET'])
def raport_pracownikow():
    rok = request.args.get('rok', type=int)
    if not rok:
        return jsonify({"error": "Musisz podać parametr 'rok'"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Liczba przesyłek przypisanych do każdego kuriera w danym roku
        cursor.execute("""
            SELECT 
                p.ID_PRACOWNIKA, 
                pr.IMIE || ' ' || pr.NAZWISKO AS pracownik,
                COUNT(*) AS liczba_przesylek
            FROM Przesylki p
            JOIN Pracownicy pr ON p.ID_PRACOWNIKA = pr.ID_PRACOWNIKA
            WHERE pr.STANOWISKO = 'kurier' AND EXTRACT(YEAR FROM p.DATA_NADANIA) = ?
            GROUP BY p.ID_PRACOWNIKA, pr.IMIE, pr.NAZWISKO
            ORDER BY liczba_przesylek DESC
        """, (rok,))
        przesylki_kurierzy = cursor.fetchall()

        # 2. Liczba urlopów dla każdego pracownika w danym roku
        cursor.execute("""
            SELECT 
                u.ID_PRACOWNIKA,
                pr.IMIE || ' ' || pr.NAZWISKO AS pracownik,
                COUNT(*) AS liczba_urlopow
            FROM Urlop u
            JOIN Pracownicy pr ON u.ID_PRACOWNIKA = pr.ID_PRACOWNIKA
            WHERE EXTRACT(YEAR FROM u.DATA_ROZPOCZECIA) = ?
            GROUP BY u.ID_PRACOWNIKA, pr.IMIE, pr.NAZWISKO
            ORDER BY liczba_urlopow DESC
        """, (rok,))
        urlopy_pracownicy = cursor.fetchall()

        # 3. Liczba urlopów w poszczególnych miesiącach
        cursor.execute("""
            SELECT 
                EXTRACT(MONTH FROM u.DATA_ROZPOCZECIA) AS miesiac,
                COUNT(*) AS liczba_urlopow
            FROM Urlop u
            WHERE EXTRACT(YEAR FROM u.DATA_ROZPOCZECIA) = ?
            GROUP BY EXTRACT(MONTH FROM u.DATA_ROZPOCZECIA)
            ORDER BY miesiac
        """, (rok,))
        urlopy_miesiace = cursor.fetchall()

    finally:
        conn.close()

    # Formatowanie danych
    raport_przesylki = [
        {"pracownik": row[1], "liczba_przesylek": row[2]} for row in przesylki_kurierzy
    ]
    raport_urlopy = [
        {"pracownik": row[1], "liczba_urlopow": row[2]} for row in urlopy_pracownicy
    ]
    urlopy_miesieczne = {int(row[0]): row[1] for row in urlopy_miesiace}

    return render_template(
        'raport_pracownikow.html',
        rok=rok,
        przesylki=raport_przesylki,
        urlopy=raport_urlopy,
        urlopy_miesiace=urlopy_miesieczne
    )


    
if __name__=='__main__':
    app.run(debug=True)
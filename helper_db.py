import sqlite3

def db_table_exists(conn, table_name):
    c = conn.cursor()
    c.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='" + table_name + "'")
    if c.fetchone()[0] == 1:
        return True
    return False

def db_record_exists(conn, table_name, field_name, field_value):
    c = conn.cursor()
    record_exists_raw = c.execute("SELECT " + field_name + " FROM " + table_name + " WHERE " + field_name + " = ?", (field_value,))
    record_exists = record_exists_raw.fetchone()
    return record_exists != None

def db_execute_query(conn, query, values = ()):
    c = conn.cursor()
    c.execute(query, values)
    conn.commit()

def db_truncate_table(conn, table_name):
    c = conn.cursor()
    c.execute("DELETE FROM " + table_name)
    conn.commit()

def db_delete_record(conn, table_name, field_name, field_value):
    c = conn.cursor()
    c.execute("DELETE FROM " + table_name + " WHERE " + field_name + "=?", (field_value,))
    conn.commit()

def extract_all_accs(conn):
    c = conn.cursor()
    c.execute("SELECT account_name FROM tw_accs")
    conn.commit()
    accs = []
    for acc in c:
        accs.append(acc[0])
    return accs

def add_acc(conn, account_name):
    if db_record_exists(conn, 'tw_accs', 'account_name', account_name):
        return False
    lid = get_last_id(conn, 'tw_accs')
    conn.execute("INSERT INTO tw_accs (id, account_name) VALUES (?, ?)", (lid, account_name))
    conn.commit()
    return True

def remove_acc(conn, account_name):
    db_delete_record(conn, 'tw_accs', 'account_name', account_name)

def get_last_id(conn, table_name):
    get_last_id_query = "SELECT id FROM " + table_name + " ORDER BY id DESC LIMIT 1"
    last_id_raw = conn.execute(get_last_id_query)
    last_id_fetched = last_id_raw.fetchone()
    if last_id_fetched == None:
        last_id = 0
    else:
        last_id = last_id_fetched[0] + 1
    return last_id

def check_acc_follows_count(conn, account_name):
    query = "SELECT count(friend_id) FROM tw_accs_data WHERE account_name = ?"
    values = (account_name,)
    numberOfRows_raw = conn.execute(query, values)
    numberOfRows = numberOfRows_raw.fetchone()[0]
    if numberOfRows == None:
        return 0
    else:
        return numberOfRows

def db_init():
    conn = sqlite3.connect('./tw.db')
    if db_table_exists(conn, 'tw_accs_data') == False:
        query = '''CREATE TABLE tw_accs_data
                    (id INT PRIMARY KEY    NOT NULL,
                    account_name    TEXT   NOT NULL,
                    friend_id       INT    NOT NULL);'''
        db_execute_query(conn, query)
    if db_table_exists(conn, 'tw_accs') == False:
        query = '''CREATE TABLE tw_accs
                    (id INT PRIMARY KEY    NOT NULL,
                    account_name   TEXT    NOT NULL);'''
        db_execute_query(conn, query)
    print("DB is prepared")
    return conn

conn = db_init()
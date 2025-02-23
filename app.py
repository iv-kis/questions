import datetime
import streamlit as st
import sqlite3
import json
import time
import random
from sqlite3 import Connection

import numpy as np
from streamlit_autorefresh import st_autorefresh


N_ATTEMPTS = 10
EXPIRY_DAYS = 7
SESSIONS_LIMIT = 1000
SHOW_MESSAGE_SECONDS = 1


def adapt_datetime(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def convert_datetime(s):
    return datetime.datetime.strptime(s.decode('utf-8'), '%Y-%m-%d %H:%M:%S')


def load_questions(file_path):
    with open(file_path, 'r') as file:
        questions = json.load(file)
    return questions


def get_shared_state(conn: Connection, session_id: str) -> int:
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT current_index FROM state WHERE id = ?', (session_id,))
    result = c.fetchone()
    return result['current_index'] if result else None


def update_shared_state(conn: Connection, session_id: str, value):
    c = conn.cursor()
    c.execute(
        'UPDATE state SET current_index = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?',
        (value, session_id)
    )
    conn.commit()


def get_started_state(conn: Connection, session_id: str) -> int:
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT started FROM state WHERE id = ?', (session_id,))
    result = c.fetchone()
    return result['started'] if result else None


def update_started_state(conn: Connection, session_id: str, value):
    c = conn.cursor()
    c.execute(
        'UPDATE state SET started = ?, last_updated= CURRENT_TIMESTAMP WHERE id = ?',
        (value, session_id)
    )
    conn.commit()


def create_session(conn: Connection) -> str:
    for _ in range(N_ATTEMPTS):
        session_id = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM state WHERE id = ?', (session_id,))
        if c.fetchone()[0] == 0:  # Check if the session ID does not exist
            c.execute(
                'INSERT INTO state (id, current_index, started, last_updated) VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
                (session_id, 0, 0)
            )
            conn.commit()
            return session_id
    raise ValueError(f"Unable to generate a unique session ID after {N_ATTEMPTS} attempts")


def clean_expired_sessions(conn: Connection):
    expiry_date = datetime.datetime.now() - datetime.timedelta(days=EXPIRY_DAYS)
    c = conn.cursor()
    c.execute('DELETE FROM state WHERE last_updated < ?', (expiry_date,))
    conn.commit()


def check_sessions_limit(conn: Connection) -> bool:
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM state')
    return c.fetchone()[0] < SESSIONS_LIMIT


def start_new_session():
    clean_expired_sessions(conn)
    if check_sessions_limit(conn):
        st.session_state.session_id = create_session(conn)
    else:
        st.warning("Maximum number of sessions reached. Please try again later.")
        time.sleep(SHOW_MESSAGE_SECONDS)


def join_session(session_id: str):
    if get_started_state(conn, session_id) is not None:
        st.session_state.session_id = session_id
    else:
        st.warning("No such session ID. Please try another one.")
        time.sleep(SHOW_MESSAGE_SECONDS)

sqlite3.register_adapter(datetime.datetime, adapt_datetime)
sqlite3.register_converter('timestamp', convert_datetime)
conn = sqlite3.connect(database='shared_state.db', detect_types=sqlite3.PARSE_DECLTYPES)

c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS state (
    id INTEGER PRIMARY KEY,
    current_index INTEGER,
    started INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

st.set_page_config(
    layout="wide",
    menu_items={
        'About': 'Apache 2.0 Licence, 2025.  \n#### Author  \n_ivkis_  \nt.helsing.t@gmail.com  \n#### Powered by  '
    }
)
st.title('Questions')

if 'session_id' not in st.session_state:
    st.session_state.session_id = None

# initial_state = get_shared_state(conn=conn)
# started = get_started_state(conn=conn)

if st.session_state.session_id is None:
    start_col, join_col = st.columns(2)
    with start_col:
        if st.button("Start"):
            start_new_session()
            st.success('New session is successfully created.')
            time.sleep(SHOW_MESSAGE_SECONDS)
            st.rerun()
    with join_col:
        st.session_state.temp_session_id = st.text_input("Enter session ID:", value="")
        if st.button("Join"):
            if st.session_state.temp_session_id:
                join_session(st.session_state.temp_session_id)
                st.rerun()

else:
    session_id = st.session_state.session_id

    if get_started_state(conn, session_id) is None:
        st.warning("Session ID no longer exists. Please start a new session or join an existing one.")
        time.sleep(SHOW_MESSAGE_SECONDS)
        st.session_state.session_id = None
        st.rerun()

    st.write(f"Session ID: {session_id}")

    initial_state = get_shared_state(conn=conn, session_id=session_id)
    started = get_started_state(conn=conn, session_id=session_id)

    questions = load_questions('questions.json')
    cols = st.columns([0.6, 0.4, 2, 0.5], gap='small')
    cols[0].button('Previous    ', key='prev_button', use_container_width=True)
    cols[1].button('Next    ', key='next_button', use_container_width=True)
    cols[3].button('Random    ', key='random_button', use_container_width=True)

    current_index = get_shared_state(conn=conn, session_id=session_id)

    if 'prev_button' in st.session_state:
        if st.session_state.prev_button and current_index > 0:
            current_index -= 1

    if 'random_button' in st.session_state:
        if st.session_state.random_button:
            current_index = np.random.randint(0, len(questions))

    if 'next_button' in st.session_state:
        if st.session_state.next_button and current_index < len(questions) - 1:
            current_index += 1

    question_content = questions[str(current_index)]['question']
    question_part = questions[str(current_index)]['part']
    st.markdown(f"### Часть {question_part}")
    st.markdown(f"##### Вопрос {current_index + 1}")
    st.markdown(f"{question_content}")
    st.markdown(f" \n  \n  ")

    update_shared_state(conn=conn, session_id=session_id, value=current_index)

    cols2 = st.columns([3, 0.5], gap='small')
    cols2[0].write('')
    cols2[1].button('Finish    ', key='finish_button', use_container_width=True)
    if st.session_state.finish_button:
        c.execute('DELETE FROM state WHERE id = ?', (session_id,))
        conn.commit()
        st.session_state.session_id = None
        st.rerun()

    count = st_autorefresh(interval=2000, key="auto_refresh")
conn.close()

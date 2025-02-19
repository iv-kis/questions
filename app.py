import streamlit as st
import sqlite3
import pandas as pd
import numpy as np


#df = pd.read_csv('messages.csv')
messages = ['message 1','message 2', 'message 3', 'message 4']

def get_random_message_index():
    return np.random.randint(0, len(messages))

def get_shared_state(conn):
    c = conn.cursor()
    c.execute('SELECT current_index FROM state WHERE id = 1')
    return c.fetchone()[0]

def update_shared_state(conn, value):
    c = conn.cursor()
    c.execute('UPDATE state SET current_index = ? WHERE id = 1', (value,))
    conn.commit()

conn = sqlite3.connect('shared_state.db')
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS state (
    id INTEGER PRIMARY KEY,
    current_index INTEGER
)
''')

if not c.execute('SELECT COUNT(*) FROM state').fetchone()[0]:
    c.execute('INSERT INTO state (id, current_index) VALUES (?, ?)', (1, 0))
    conn.commit()

st.title('Questions')

if 'button_clicked' not in st.session_state:
    st.session_state.button_clicked = False
    if st.button("Start", key="start_button"):
        st.session_state.button_clicked = True
else:
    cols = st.columns([0.6, 0.4, 2, 0.5], gap='small')
    cols[0].button('Previous    ', key='prev_button', use_container_width=True)
    cols[1].button('Next    ', key='next_button', use_container_width=True)
    cols[3].button('Random    ', key='random_button', use_container_width=True)

    current_index = get_shared_state(conn=conn)

    if 'prev_button' in st.session_state:
        if st.session_state.prev_button and current_index > 0:
            current_index -= 1

    if 'random_button' in st.session_state:
        if st.session_state.random_button:
            current_index = get_random_message_index()

    if 'next_button' in st.session_state:
        if st.session_state.next_button and current_index < len(messages) - 1:
            current_index += 1

    update_shared_state(conn=conn, value=current_index)

    st.text_area('Question', f"{messages[current_index]}", height=200, disabled=True)

conn.close()

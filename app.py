import streamlit as st
import sqlite3
import json
import numpy as np

def load_questions(file_path):
    with open(file_path, 'r') as file:
        questions = json.load(file)
    return questions

def get_shared_state(conn) -> int:
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

st.set_page_config(layout="wide")
st.title('Questions')

initial_state = get_shared_state(conn=conn)

if 'start_button_clicked' not in st.session_state:
    st.session_state.start_button_clicked = False

if not st.session_state.start_button_clicked and initial_state == 0:
    if st.button(f"Start", key="start_button"):
        st.session_state.start_button_clicked = True
        st.rerun()

else:
    questions = load_questions('questions.json')
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

    update_shared_state(conn=conn, value=current_index)

    cols2 = st.columns([3, 0.5], gap='small')
    cols2[0].write('')
    cols2[1].button('Finish    ', key='finish_button', use_container_width=True)
    if st.session_state.finish_button:
        update_shared_state(conn=conn, value=0)
        st.session_state.start_button_clicked = False
        conn.close()
        st.rerun()

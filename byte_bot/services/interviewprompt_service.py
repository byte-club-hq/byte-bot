import json
import random

# Loads the question:answer from the json file
with open("byte_bot/data/interview_questions.json") as f:
    QUESTIONS = json.load(f)

def get_random_question():
    return random.choice(QUESTIONS)
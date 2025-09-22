# question_generator.py
import os
import json
import random
from config import DATA_DIR
from data_processor import DataProcessor

def generate_questions_from_dataset(n=1200):
    """
    If dataset available, extract teams, years, players and produce targeted questions.
    Falls back to high-coverage templates if dataset is not populated.
    """
    dp = DataProcessor()
    dp.load_json_files()
    teams = set()
    players = set()
    years = set()
    for filename, data in dp.matches_data:
        info = data.get("info", {}) or {}
        for t in info.get("teams", []) or []:
            teams.add(t)
        for p_dict in (info.get("players") or {}).values() if info.get("players") else []:
            for p in p_dict:
                players.add(p)
        dates = info.get("dates") or []
        if dates:
            years.add(dates[0][:4])
    years_list = sorted(list(years)) if years else [str(y) for y in range(2003,2024)]
    teams_list = sorted(list(teams)) if teams else ["India","Australia","England","Pakistan","South Africa","New Zealand","Sri Lanka","West Indies","Bangladesh","Afghanistan"]
    players_list = sorted(list(players)) if players else ["V Kohli","RG Sharma","DA Warner","TM Head","SPD Smith","GJ Maxwell","JJ Bumrah","PJ Cummins"]

    templates = [
        "Who won the {year} Cricket World Cup final?",
        "What was the final score of the {year} World Cup final and which team won?",
        "Who was the player of the match in the {year} World Cup final?",
        "Which teams reached the semi-finals in {year}?",
        "Who scored the most runs in the {year} tournament?",
        "Who took the most wickets in the {year} tournament?",
        "Which player had the highest individual score in {year} World Cup?",
        "Which bowler had the best bowling figures in a single match in {year}?",
        "Which matches in {year} were decided by less than 10 runs?",
        "Which team had the highest run aggregate in {year}?"
    ]
    questions = []
    while len(questions) < n:
        year = random.choice(years_list)
        tpl = random.choice(templates)
        player = random.choice(players_list)
        team = random.choice(teams_list)
        try:
            q = tpl.format(year=year, player=player, team=team)
        except Exception:
            q = tpl.format(year=year)
        questions.append(q)
    out = os.path.join(DATA_DIR, "generated_questions.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"count": len(questions), "questions": questions}, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(questions)} questions to {out}")
    return out

if __name__ == "__main__":
    generate_questions_from_dataset(1200)

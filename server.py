from pickle import encode_long
from flask import Flask, render_template, request
from forsan import playerStat, teamComposition, matchStats, mapStats, forsen
from datetime import datetime, timedelta
from faceit import match
import json, os, psycopg, threading

sem = threading.Semaphore()


app = Flask(__name__)

with open("codes.json") as jsonFile:
    country_codes = json.load(jsonFile)

psql_url = os.environ["DATABASE_URL"]

current_match = forsen.get_past_matches(1)[0]
current_match_id = current_match.match_id


last_exec = datetime.now()

#hello

@app.route("/")
def mainView():
    global current_match

    forsen.update()

    forsens_team_wp = round(((current_match.forsens_team.avg_elo - current_match.other_team.avg_elo) / (current_match.forsens_team.avg_elo + current_match.other_team.avg_elo)) * 100 + 50)
    
    return render_template("main.html",
    match=current_match, ft_wp = str(forsens_team_wp), ot_wp = str(100 - forsens_team_wp),
    forsen_stat_spam = playerStat(), team_comp_spam = teamComposition(current_match),
    match_stat_spam = matchStats(current_match), map_stat_spam = mapStats(current_match), 
    map_stats = forsen.get_map_stats(current_match.map), country_table = country_codes,
    forsen = forsen, progress = forsen.get_level_progress())

@app.route("/faceit_webhook", methods = ["POST"])
def faceit_webhook():
    global current_match_id,last_exec
    data = request.json
    secret = request.args.get("Secret")
    print(f'Webhook received: {data["event"]} {data["payload"]["id"]} {secret}', flush=True)

    print(data, flush=True)

    if (not secret):
        print(f"Webhook Rejected: no secret provided", flush=True)
        return "no secret provided"
    
    if (secret != os.environ["webhook_secret"]):
        print("Wrong app_id Provided", flush=True)
        return "wrong secret provided"


    current_match_id = data["payload"]["id"]
    last_exec = datetime.now()
    return "data received"

@app.route("/get_status", methods = ["GET"])
def send_stat():
    global current_match, current_match_id, last_exec, rewards_distributed
    sem.acquire()
    if (datetime.now() - last_exec).total_seconds() > 5:

        for attempt in range(5):
            try:
                current_match = match(current_match_id)
                break
            except Exception as e:
                print(f"Match update attempt {attempt} failed!")
                print(str(e))

        last_exec = datetime.now() + timedelta(seconds = 10)
    sem.release()
    return({"match_id":current_match.match_id, "round":current_match.forsens_team.score + current_match.other_team.score + 1, "ft_s":current_match.forsens_team.score, "ot_s":current_match.other_team.score})



@app.route("/gamba")
def gamba():
    with psycopg.connect(psql_url) as conn:
            records = conn.execute('SELECT RANK() OVER (ORDER BY points DESC) ranking, "username", "points" FROM "public"."users" ORDER BY "points" DESC;').fetchall()
            return render_template("gamba.html", top_users=records)


if __name__ == "__main__":
    app.run(debug=True)



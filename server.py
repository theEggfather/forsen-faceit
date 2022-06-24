from flask import Flask, render_template, request
from flask_login import LoginManager, current_user, login_user, logout_user
import flask_login
from forsan import playerStat, teamComposition, matchStats, mapStats, forsen
from datetime import datetime, timedelta
from faceit import match
import json, os, psycopg, re, bcrypt, threading

sem = threading.Semaphore()


app = Flask(__name__)
app.secret_key = bytes(os.environ["app_secret"], "utf-8")

login_manager = LoginManager()
login_manager.init_app(app)

with open("codes.json") as jsonFile:
    country_codes = json.load(jsonFile)

psql_url = os.environ["DATABASE_URL"]

current_match = forsen.get_past_matches(1)[0]
current_match_id = current_match.match_id

rewards_distributed = False

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
    map_stats = forsen.get_map_stats(current_match.map), country_table = country_codes)

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
        current_match = match(current_match_id)
        last_exec = datetime.now() + timedelta(seconds = 10)
        if current_match.finished and not rewards_distributed:
            distributePredictions(current_match.match_id, current_match.winner_id == current_match.forsens_team.team_id)
            rewards_distributed = True
        if current_match.status == "READY":
            rewards_distributed = False
    sem.release()
    return({"match_id":current_match.match_id, "round":current_match.forsens_team.score + current_match.other_team.score + 1, "ft_s":current_match.forsens_team.score, "ot_s":current_match.other_team.score})


def distributePredictions(match_id, forsenWon):
    with psycopg.connect(psql_url) as conn:
        predictions = conn.execute('SELECT username, user_id, ft_pred, ot_pred FROM PUBLIC.predictions WHERE match_id = %s', (match_id,)).fetchall()
        if len(predictions) == 0:
            return
        total_ft_pred = sum([pred[2] for pred in predictions])
        total_ot_pred = sum([pred[3] for pred in predictions])
        total_pred = total_ft_pred + total_ot_pred
        if total_pred == 0:
            return
        for prediction in predictions:
            predictor = prediction[1]
            pred_amount = prediction[2] if forsenWon else prediction[3]
            pred_prize = round(total_pred * (pred_amount / max(1, total_ft_pred if forsenWon else total_ot_pred)))
            conn.execute('UPDATE PUBLIC.users SET points = points + %s, last_won = %s  WHERE id = %s', (pred_prize, pred_prize, predictor))


@app.route("/gamba", methods=["GET", "POST"])
def gamba():
    if request.method == "GET":
        forsens_team_wp = round(((current_match.forsens_team.avg_elo - current_match.other_team.avg_elo) / (current_match.forsens_team.avg_elo + current_match.other_team.avg_elo)) * 100 + 50)

        with psycopg.connect(psql_url) as conn:
            records = conn.execute('SELECT RANK() OVER (ORDER BY points DESC) ranking, "username", "points" FROM "public"."users" ORDER BY "points" DESC LIMIT 10; ').fetchall()
            ft_pred_sum, ot_pred_sum = conn.execute('SELECT SUM("ft_pred"), SUM("ot_pred") FROM "public"."predictions" WHERE "match_id" = %s', (current_match_id,)).fetchone()
            if ft_pred_sum == None:
                ft_pred_sum, ot_pred_sum = (0,0)
            ft_predictors = conn.execute('SELECT username, ft_pred FROM "public"."predictions" WHERE match_id = %s  ORDER BY "ft_pred" DESC;', (current_match_id,)).fetchall()
            ot_predictors = conn.execute('SELECT username, ot_pred FROM "public"."predictions" WHERE match_id = %s  ORDER BY "ot_pred" DESC;', (current_match_id,)).fetchall()
        return render_template("gamba.html", match=current_match, top_users = records, ft_wp = str(forsens_team_wp), ot_wp = str(100 - forsens_team_wp),
                                ft_pred_sum = ft_pred_sum, ot_pred_sum = ot_pred_sum, ft_pred_perc = round(100 * (max(ft_pred_sum,1) / max(ft_pred_sum + ot_pred_sum,2))),
                                ot_pred_perc = round(100 * (max(ot_pred_sum,1) / max(ft_pred_sum + ot_pred_sum,2))), ft_predictors = ft_predictors, ot_predictors = ot_predictors )

    elif request.method == "POST":
        data = request.json

        if data["action"] == "register":

            if (len(re.findall(r"^(?=.{4,20}$)(?!.*[_.]{2})[a-zA-Z0-9._]+$",data["username"])) == 0):
                return {"response":"Invalid Username Provided"}

            with psycopg.connect(psql_url) as conn:
                count = conn.execute('SELECT COUNT(*) FROM "public"."users" WHERE "username" = %s;', (data["username"],)).fetchone()[0]
                if (count != 0):
                    return {"response":"Username Already Taken"}
                salt = bcrypt.gensalt()
                pass_hash = bcrypt.hashpw(bytes(data["password_hash"], "utf-8"),salt)
                sql_args = {"username": data["username"], "points":1000, "pass_hash":pass_hash.decode("utf-8"), "salt":salt.decode("utf-8")}
                conn.execute('INSERT INTO "public"."users" ("username", "points", "last_access", "pass_hash", "pass_salt", "last_redeem") VALUES (%(username)s, %(points)s, CURRENT_TIMESTAMP, %(pass_hash)s, %(salt)s, CURRENT_TIMESTAMP);',sql_args)
            login_user(User(data["username"]))
            return {"response":f"Account {data['username']} Created"}
        
        elif data["action"] == "login":
            with psycopg.connect(psql_url) as conn:
                count = conn.execute('SELECT COUNT(*) FROM "public"."users" WHERE "username" = %s;', (data["username"],)).fetchone()[0]
                if (count != 1):
                    return {"response":"Wrong Username"}
                hash, salt = conn.execute('SELECT pass_hash,pass_salt FROM "public"."users" WHERE "username" = %s;',(data["username"],)).fetchone()
                input_hash = bcrypt.hashpw(bytes(data["password_hash"], "utf-8"), bytes(salt, "utf-8")).decode("utf-8")
                if hash != input_hash:
                    return {"response":"Wrong Password"}
                login_user(User(data["username"]))
                conn.execute('UPDATE "public"."users" SET "last_access"=CURRENT_TIMESTAMP WHERE  "username"=%s;', (data["username"],))
            return {"response":"Login Succesful"}
            
        elif data["action"] == "logout":
            logout_user()
            return {"response":"Logged Out"}
        
        elif data["action"] == "redeem":
            if current_user.is_authenticated:
                sem.acquire()
                with psycopg.connect(psql_url) as conn:
                    last_redeemed = conn.execute('SELECT "last_redeem" FROM "public"."users" WHERE "id" = %s;', (current_user.get_id(),)).fetchone()[0]
                    conn.execute('UPDATE "public"."users" SET "last_redeem"=CURRENT_TIMESTAMP WHERE "id"=%s;', (current_user.get_id(),))
                    points_gained = (datetime.now() - last_redeemed).total_seconds() / 60.0 #minutes since last redeemed
                    points_gained = round(min(2000, 10 * points_gained)) # 10 points per min, capped at 2000
                    conn.execute('UPDATE "public"."users" SET "points" = "points" + %s WHERE "id" = %s;', (points_gained, current_user.get_id()))
                    sem.release()
                    return {"response":f"{points_gained} points redeemed."}
            else:
                return {"response":"Please login to redeem!"}
        
        elif data["action"] == "predict":
            if current_user.is_authenticated:
                if 1 < current_match.forsens_team.score + current_match.other_team.score + 1 < 6 and current_match.finished == False:
                    ft_pred, ot_pred = int(data["ft_pred"]) if data["ft_pred"] != "" else 0, int(data["ot_pred"]) if data["ot_pred"] != "" else 0
                    ft_pred = max(ft_pred, 0)
                    ot_pred = max(ot_pred, 0)
                    if current_user.points > ft_pred + ot_pred:
                        with psycopg.connect(psql_url) as conn:
                            conn.execute('INSERT INTO "public"."predictions" ("user_id", "username", "ft_pred", "ot_pred", "match_id") VALUES (%s, %s, %s, %s, %s);',(current_user.get_id(), current_user.username, ft_pred, ot_pred, current_match_id))
                            conn.execute('UPDATE "public"."users" SET "points" = "points" - %s WHERE "id" = %s;', (ft_pred + ot_pred, current_user.get_id()))
                            return {"response":"Prediction submitted!"}
                    else:
                        return {"response":"Not enough points!"}
                else:
                    return {"response":"Predictions are closed!"}
            else:
                return {"response":"Please login to predict!"}
    
    
    return  {"response":"Bad Request"}



class User(flask_login.UserMixin):
    def __init__(self, username, with_id=False) -> None:
        with psycopg.connect(psql_url) as conn:
            super().__init__()
            if with_id:
                users = conn.execute('SELECT username FROM "public"."users" WHERE id=%s;',(username,)).fetchall()
                if len(users) != 1:
                    return None
                else:
                    self.username = users[0][0]
            else:
                self.username = username
        
            self.id, self.points, self.rank, self.last_won = conn.execute('SELECT id, points, ranking, last_won FROM (SELECT *, RANK() OVER (ORDER BY points DESC) AS ranking FROM "public"."users" ) AS rt WHERE "username" = %s;',(self.username,)).fetchone()



    def get_points(self):
        with psycopg.connect(psql_url) as conn:
            self.points = conn.execute('SELECT points FROM "public"."users" WHERE "username" = %s;',(self.username,)).fetchone()[0]

@login_manager.user_loader
def load_user(user_id):
    return User(user_id, with_id=True)

if __name__ == "__main__":
    app.run(debug=True)



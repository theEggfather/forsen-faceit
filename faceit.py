import os, requests, json
from datetime import datetime, timedelta

time_zone = 2 # in UTC + 2 format

class match:

    def __init__(self, match_id) -> None:

        headers = {
            'accept': 'application/json',
            'Authorization': "Bearer " + os.environ["server_api_key"],
        }
         
        while True:
            _response = requests.get(f'https://open.faceit.com/data/v4/matches/{match_id}', headers=headers)
            if _response.status_code != 503: 
                break
        
        if _response.status_code != 200: 
            raise Exception(f"Bad match_id response, code {_response.status_code}")
        
        _response = json.loads(_response.content)
        self.team1 = team(_response["teams"]["faction1"]["roster"],_response["teams"]["faction1"]["faction_id"], _response.get("results",{"score":{"faction1":0}})["score"]["faction1"])
        self.team2 = team(_response["teams"]["faction2"]["roster"],_response["teams"]["faction2"]["faction_id"], _response.get("results",{"score":{"faction2":0}})["score"]["faction2"])
        self.map = _response["voting"]["map"]["entities"][0]["game_map_id"]
        self.map_name = _response["voting"]["map"]["entities"][0]["name"]
        self.map_url = _response["voting"]["map"]["entities"][0]["image_sm"]
        self.match_id = match_id

        self.elo_diff = self.team1.avg_elo - self.team2.avg_elo

        self.team1.setEloChangeOnWin(round(50 / (1 + pow(10, self.elo_diff / 400))))
        self.team2.setEloChangeOnWin(round(50 / (1 + pow(10, -self.elo_diff / 400))))

        self.forsens_team = self.team2
        self.other_team = self.team1
        for member in self.team1.players:
            if member.player_id == "ea1864f6-5748-41e1-a084-1e5c0044322d":
                self.forsens_team = self.team1
                self.other_team = self.team2

        
        self.finished = False
        self.status = _response["status"]

        if _response["status"] == "FINISHED":
            self.finished = True
            self.finish_time = _response["finished_at"]
            while True:
                match_stats = _response = requests.get(f'https://open.faceit.com/data/v4/matches/{match_id}/stats', headers=headers)
                if _response.status_code != 503: 
                    break
            if _response.status_code != 200: 
                raise Exception(f"Bad match_id/stats response, code {match_stats.status_code}")

            match_stats = json.loads(match_stats.content)
            _scores = match_stats["rounds"][0]["round_stats"]["Score"].split(" / ")
            _scores = [int(score) for score in _scores]
            self.winner_score = max(_scores)
            self.loser_score = min(_scores)
            self.winner_id = match_stats["rounds"][0]["round_stats"]["Winner"]
            

        pass

class team:
    def __init__(self, roster, team_id, score) -> None:
        self.players = []
        for i in range(5):
            id = roster[i]["player_id"]
            member = player(id)
            self.players.append(member)
        total_elo = 0
        for member in self.players:
            total_elo += member.elo
        
        self.avg_elo = round(total_elo / 5)
        self.team_id = team_id

        lvltable = [0,0,800,950,1100,1250,1400,1550,1700,1850,2000]
        for i in range(1,11):
            if self.avg_elo > lvltable[i]:
                self.level = i

        self.score = score
        self.eloChangeOnWin = 0

        pass
    
    def setEloChangeOnWin(self, eloChange):
        self.eloChangeOnWin = eloChange

    def __eq__(self, __o: object) -> bool:
        return ((isinstance(__o, team)) & (self.team_id == __o.team_id))
        pass


class player:

    def __init__(self, player_id) -> None:

        headers = {
            'accept': 'application/json',
            'Authorization': "Bearer " + os.environ["server_api_key"],
        }
        while True:
            _response = requests.get(f'https://open.faceit.com/data/v4/players/{player_id}', headers=headers)
            if _response.status_code != 503: 
                break
        if _response.status_code != 200: 
            raise Exception(f"Bad player_id response, code {_response.status_code}")
        
        _response = json.loads(_response.content)

        self.nickname = _response["nickname"]
        self.country = _response["country"]
        self.level = _response["games"]["csgo"]["skill_level"]
        self.elo = _response["games"]["csgo"]["faceit_elo"]
        self.player_id = player_id
        self.player_avatar_url = _response["avatar"]

        pass

    def update(self):
        headers = {
            'accept': 'application/json',
            'Authorization': "Bearer " + os.environ["server_api_key"],
        }
        while True:
            _response = requests.get(f'https://open.faceit.com/data/v4/players/{self.player_id}', headers=headers)
            if _response.status_code != 503: 
                break
        if _response.status_code != 200: 
            raise Exception(f"Bad player_id response, code {_response.status_code}")
        
        _response = json.loads(_response.content)

        self.nickname = _response["nickname"]
        self.country = _response["country"]
        self.level = _response["games"]["csgo"]["skill_level"]
        self.elo = _response["games"]["csgo"]["faceit_elo"]
        self.player_avatar_url = _response["avatar"]

        pass

    def __eq__(self, __o: object) -> bool:
        return (isinstance(__o,player) & (self.player_id == __o.player_id))
        pass

    def get_past_matches(self, match_count):

        self.past_matches = []
        headers = {
        'accept': 'application/json',
        'Authorization': "Bearer " + os.environ["server_api_key"],
        }

        params = {
            'game': 'csgo',
            'offset': '0',
            'limit': str(match_count),
        }
        while True:
            _response = requests.get(f'https://open.faceit.com/data/v4/players/{self.player_id}/history', params=params, headers=headers)
            if _response.status_code != 503:
                break
        if _response.status_code != 200: 
            raise Exception(f"Bad player_id/history response, code {_response.status_code}")
        _response = json.loads(_response.content)

        for i in range(match_count):
            self.past_matches.append(match(_response["items"][i]["match_id"]))
        
        return self.past_matches

    def get_map_stats(self,map):
        headers = {
            'accept': 'application/json',
            'Authorization': "Bearer " + os.environ["server_api_key"],
        }
        while True:
            _response = requests.get(f'https://open.faceit.com/data/v4/players/{self.player_id}/stats/csgo', headers=headers)
            if _response.status_code != 503:
                break
        if _response.status_code != 200: 
            raise Exception(f"Bad player_id/stats response, code {_response.status_code}")
        
        _response = json.loads(_response.content)
        _response = _response["segments"]
        for map_data in _response:
            if map_data["label"] == map:
                return {"map" : map, "played":map_data["stats"]["Matches"], "win_rate": map_data["stats"]["Win Rate %"], "K/D":map_data["stats"]["Average K/D Ratio"]}
        else:
            return {"map":map, "played":0,"win_rate":0,"K/D":0}

    def get_level_progress(self):
        lvltable = [0,0,800,950,1100,1250,1400,1550,1700,1850,2000]
        level_diff = lvltable[self.level + 1] - lvltable[self.level]
        level_progress = self.elo - lvltable[self.level]
        level_perc = round(100 * (level_progress / level_diff), 2)
        return (level_perc, lvltable[self.level], lvltable[self.level + 1])


    
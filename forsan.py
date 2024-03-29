# -*- coding: utf-8 -*-

import math
import faceit
from datetime import datetime


forsen = faceit.player("ea1864f6-5748-41e1-a084-1e5c0044322d")



def offlineStats(matches):
    forsen.get_past_matches(matches)
    out = "/me forsenE OFFLINE RECAP "
    for i in range(matches):
        match = forsen.past_matches[i]
        if forsen in match.team1.players:
            forsens_team = match.team1
        else:
            forsens_team = match.team2
            
        status = "Win" if (forsens_team.team_id == match.winner_id) else "Loss"
        out += f"|{match.finish_time.time()} {match.map} {match.winner_score}/{match.loser_score} {status} forsenE "
    
    return out + "\n"

def playerStat(player = forsen):
    elo = player.elo
    lvltable = [0,0,800,950,1100,1250,1400,1550,1700,1850,2000]
    ranktable = [0,1099,1499,1849,1999]
    ranks = ["Bronze", "Silver", "Gold", "Diamond", "Master"]

    for i in range(5):
        if elo > ranktable[i]:
            rank = ranks[i]
            rank_i = i
    
    progress = forsen.get_level_progress();

    out = f"/me —— forsenE STATS —— forsenE is forsenLevel LVL {player.level}, {rank} rank with {player.elo} ELO | ⠀  forsenE needs {lvltable[player.level + 1] - player.elo} elo to level up! forsenLevel TeaTime {makeBar(progress[0])} {progress[0]}%"
    return out + "\n"

def makeBar(p):
    #adapted from https://github.com/Changaco/unicode-progress-bars/blob/master/generator.html
    size = 28
    style = '░▒▓█'
    full_sym = style[-1]
    n = len(style) -1
    if p == 100:
        return full_sym * size
    p /= 100.0
    x = p * size
    full = math.floor(x)
    rest = x - full
    middle = math.floor(rest * n)
    if p != 0 and full == 0 and middle == 0:
        middle = 1
    m = "" if full == size else style[middle]
    return full_sym * full + m + style[0] * (size - full - 1)


def teamComposition(match):
    if forsen in match.team1.players:
        forsens_team = match.team1
    else:
        forsens_team = match.team2
    out = f"/me forsenScoots TEAM COMPOSITION: forsenE lvl {forsen.level} "
    for member in forsens_team.players:
        if member != forsen:
            if member.country not in []:
                out += f", :flag-{member.country}: lvl {member.level}"
            else:
                out += f", {member.country} lvl {member.level}"
    return out + " forsenScoots " + "\n"

def matchStats(match):
    if forsen in match.team1.players:
        forsens_team = match.team1
        other_team = match.team2
    else:
        forsens_team = match.team2
        other_team = match.team1
    out = f"/me forsenE IS LEVEL {forsen.level} ⠀⠀⠀⠀ ‎forsenE 's team: {round(((forsens_team.avg_elo - other_team.avg_elo) / (forsens_team.avg_elo + other_team.avg_elo)) * 100 + 50)}% win prob, Avg. lvl. {forsens_team.level}, {forsens_team.avg_elo} rating ⠀⠀Against: {round(((other_team.avg_elo - forsens_team.avg_elo) / (forsens_team.avg_elo + other_team.avg_elo)) * 100 + 50)}% win prob, Avg. lvl. {other_team.level}, {other_team.avg_elo} rating ⠀—————— MATCH STATISTICS ——————"
    return out + "\n"

def mapStats(match):
    map_stats = forsen.get_map_stats(match.map)
    if int(map_stats["played"]) > 0:
        return f'/me —— MAP STATS —— forsenE has played {map_stats["map"]} {map_stats["played"]} times before, with a win rate of {map_stats["win_rate"]}%, and average K/D ratio of {map_stats["K/D"]} ⠀⠀ ——————— MAP STATISTICS ———————' + "\n"
    else:
        return f"/me —— MAP STATS —— forsenE hasn't played {match.map} before! pepeLaugh TeaTime " + "\n"

def matchFunctions(match_id):
    match = faceit.match(match_id)
    print(playerStat())
    print(teamComposition(match))
    print(matchStats(match))
    print(mapStats(match))
    return


if __name__ == "__main__":

    save_pasta = "dummy"
    while save_pasta not in ["y","n",""]:
        save_pasta = input("Archive Output y/(n):")

    if save_pasta == "y":
        save_file = open(datetime.today().strftime('%Y-%m-%d') + ".txt","w")

    outputs = []

    offline_stat = offlineStats(int(input("Offline Match Count:")))
    outputs.append(offline_stat)
    print(offline_stat)


    player_stat = playerStat()
    outputs.append(player_stat)
    print(player_stat)

    match_id = input("match id:")
    if (match_id == ""):
        print("no match id provided")
    else:
        match = faceit.match(match_id)

        team_comp = teamComposition(match)
        #outputs.append(team_comp)
        print(team_comp)

        match_stats = matchStats(match)
        #outputs.append(match_stats)
        print(match_stats)

        map_stats = mapStats(match)
        #outputs.append(map_stats)
        print(map_stats)

    if save_pasta == "y":
        print("Saving pasta...")
        save_file.writelines(outputs)


    pass

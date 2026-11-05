from __future__ import annotations

import math
import random
from datetime import datetime, timezone

HOME = [
    (1,'Leo Carter','GK','Goalkeeper',8,50),(2,'Mason Grant','RB','Right-Back',23,82),(4,'Theo Stone','CB','Centre-Back',30,68),(5,'Rafael Diaz','CB','Centre-Back',30,33),(3,'Elliot Hall','LB','Left-Back',23,17),
    (6,'Jordan Reed','DM','Defensive Midfield',45,51),(8,'Aiden Khan','CM','Central Midfield',56,64),(10,'Min Park','AM','Attacking Midfield',62,38),(7,'Lucas Silva','RW','Right Winger',72,78),(9,'Ethan Cole','ST','Centre-Forward',79,50),(11,'Marco Reyes','LW','Left Winger',72,22)
]
AWAY = [
    (31,'Noah Hart','GK','Goalkeeper',92,50),(22,'Ben Walker','RB','Right-Back',77,18),(5,'Mateo Costa','CB','Centre-Back',70,34),(4,'Owen Price','CB','Centre-Back',70,66),(3,'Samir Ali','LB','Left-Back',77,82),
    (16,'Kai Morgan','DM','Defensive Midfield',56,43),(8,'Andre Costa','CM','Central Midfield',51,63),(20,'Milo Jensen','AM','Attacking Midfield',43,50),(7,'Rico Santos','RW','Right Winger',33,20),(9,'Julian North','ST','Centre-Forward',22,50),(11,'Daniel Kim','LW','Left Winger',33,80)
]


class DemoMatchEngine:
    """Independent deterministic-ish simulation engine for one viewer/session."""

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else random.SystemRandom().randint(1, 2_000_000_000)
        self.rng = random.Random(self.seed)
        self.minute = 67
        self.home_score = 2
        self.away_score = 1
        self.home_xg = 1.43
        self.away_xg = 1.15
        self.home_possession = 49
        self.events = [
            {'minute':12,'type':'goal','team':'North London FC','player':'Ethan Cole','shirt_number':9,'assist':'Marco Reyes','text':'Right-footed finish from the centre of the box.','score':'1–0'},
            {'minute':38,'type':'goal','team':'Manchester Blue','player':'Julian North','shirt_number':9,'assist':'Rico Santos','text':'Equalizer after a fast transition.','score':'1–1'},
            {'minute':54,'type':'yellow','team':'Manchester Blue','player':'Kai Morgan','shirt_number':16,'assist':None,'text':'Yellow card for stopping a counterattack.','score':'1–1'},
            {'minute':61,'type':'chance','team':'North London FC','player':'Min Park','shirt_number':10,'assist':'Aiden Khan','text':'High-quality chance saved by Noah Hart.','score':'1–1'},
            {'minute':64,'type':'goal','team':'North London FC','player':'Marco Reyes','shirt_number':11,'assist':'Min Park','text':'Low finish after an overload on the left.','score':'2–1'},
        ]
        self.subs_done = False

    @classmethod
    def from_state(cls, state: dict) -> 'DemoMatchEngine':
        engine = cls(seed=int(state.get('seed', 1)))
        engine.minute = int(state.get('minute', 67))
        engine.home_score = int(state.get('home_score', 2))
        engine.away_score = int(state.get('away_score', 1))
        engine.home_xg = float(state.get('home_xg', 1.43))
        engine.away_xg = float(state.get('away_xg', 1.15))
        engine.home_possession = int(state.get('home_possession', 49))
        engine.events = list(state.get('events') or engine.events)
        engine.subs_done = bool(state.get('subs_done', False))
        rng_state = state.get('rng_state')
        if rng_state:
            try:
                engine.rng.setstate(_to_tuple(rng_state))
            except Exception:
                pass
        return engine

    def to_state(self) -> dict:
        return {
            'seed': self.seed,
            'minute': self.minute,
            'home_score': self.home_score,
            'away_score': self.away_score,
            'home_xg': self.home_xg,
            'away_xg': self.away_xg,
            'home_possession': self.home_possession,
            'events': self.events,
            'subs_done': self.subs_done,
            'rng_state': self.rng.getstate(),
        }

    def player(self, p, side):
        number, name, role, position, x, y = p
        wobble = math.sin((self.minute + number) * 0.31) * 1.8
        return {
            'id': f'{side}-{number}', 'name': name, 'shirt_number': number, 'role': role,
            'position': position, 'x': round(x + wobble, 1),
            'y': round(y + math.cos((self.minute + number) * .23) * 1.5, 1),
            'rating': round(6.4 + ((number * 13 + self.minute) % 24) / 10, 1),
        }

    def tick(self) -> dict:
        if self.minute < 90 and self.rng.random() > .28:
            self.minute += 1
        self.home_xg += self.rng.uniform(0, .018)
        self.away_xg += self.rng.uniform(0, .014)
        self.home_possession = max(43, min(58, self.home_possession + self.rng.choice([-1, 0, 0, 0, 1])))
        if self.minute >= 72 and not self.subs_done:
            self.subs_done = True
            self.events.append({'minute':72,'type':'substitution','team':'North London FC','player':'Noah Bennett','shirt_number':19,'assist':None,'text':'#19 Noah Bennett ON • #7 Lucas Silva OFF','score':f'{self.home_score}–{self.away_score}'})
        if self.minute < 89 and self.rng.random() < .018:
            team_home = self.rng.random() < .53
            pool = HOME[6:] if team_home else AWAY[6:]
            scorer = self.rng.choice(pool)
            assist = self.rng.choice([p for p in pool if p != scorer])
            if team_home:
                self.home_score += 1
                team = 'North London FC'
            else:
                self.away_score += 1
                team = 'Manchester Blue'
            self.events.append({'minute':self.minute,'type':'goal','team':team,'player':scorer[1],'shirt_number':scorer[0],'assist':assist[1],'text':'Simulated Demo Lab goal generated by the event engine.','score':f'{self.home_score}–{self.away_score}'})
        home_players = [self.player(p, 'home') for p in HOME]
        away_players = [self.player(p, 'away') for p in AWAY]
        return {
            'mode': 'demo',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'match': {
                'id':'demo-001','status':'IN_PLAY','minute':self.minute,'venue':'Intelligence Arena','competition':{'code':'DEMO','name':'Demo Lab','emblem':None},
                'home_team':{'id':'demo-home','name':'North London FC','short_name':'North London','crest':None},
                'away_team':{'id':'demo-away','name':'Manchester Blue','short_name':'Manchester Blue','crest':None},
                'score':{'home':self.home_score,'away':self.away_score,'half_home':1,'half_away':1},
            },
            'lineups':{'home':{'formation':'4-3-3','players':home_players},'away':{'formation':'4-2-3-1','players':away_players}},
            'ball':{'x':round(50+math.sin(self.minute*.41)*28,1),'y':round(50+math.cos(self.minute*.27)*30,1)},
            'analytics':{
                'xg':{'home':round(self.home_xg,2),'away':round(self.away_xg,2)},
                'possession':{'home':self.home_possession,'away':100-self.home_possession},
                'shots':{'home':15+max(0,self.minute-67)//9,'away':11+max(0,self.minute-67)//11},
                'shots_on_target':{'home':7,'away':5},'pass_accuracy':{'home':86,'away':90},
                'corners':{'home':5,'away':4},'pressing_index':{'home':7.8,'away':7.1},
            },
            'events': self.events[-10:][::-1],
        }


def _to_tuple(value):
    if isinstance(value, list):
        return tuple(_to_tuple(x) for x in value)
    return value

export type Team = {
  id:string; name:string; short_name?:string|null; tla?:string|null; crest?:string|null;
  venue?:string|null; founded?:number|null; club_colors?:string|null; website?:string|null; coach?:string|null; squad?:Player[]
}
export type Player = {
  id:string; name:string; position?:string|null; shirt_number?:number|null; nationality?:string|null;
  date_of_birth?:string|null; role?:string; x?:number; y?:number; rating?:number
}
export type Lineup={formation?:string|null;coach?:string|null;lineup:Player[];bench:Player[]}
export type GoalEvent={minute?:number|null;injury_time?:number|null;type?:string|null;team:Team;scorer:Player;assist?:Player|null;score:{home?:number|null;away?:number|null}}
export type BookingEvent={minute?:number|null;team:Team;player:Player;card?:string|null}
export type SubstitutionEvent={minute?:number|null;team:Team;player_out:Player;player_in:Player}
export type TimelineEvent={minute?:number|null;kind:'goal'|'booking'|'substitution';team:Team;primary:Player;secondary?:Player|null;meta?:string|null;score?:{home?:number|null;away?:number|null}|null}
export type Match = {
  id:string; utc_date?:string; status:string; minute?:number|null; injury_time?:number|null; venue?:string|null; attendance?:number|null;
  competition:{id?:string|null; code?:string|null; name?:string|null; emblem?:string|null}; home_team:Team; away_team:Team;
  score:{home?:number|null;away?:number|null;half_home?:number|null;half_away?:number|null;regular_home?:number|null;regular_away?:number|null;extra_home?:number|null;extra_away?:number|null;penalty_home?:number|null;penalty_away?:number|null;winner?:string|null;duration?:string|null}; matchday?:number|null;stage?:string|null;
  home_lineup?:Lineup; away_lineup?:Lineup; goals?:GoalEvent[]; bookings?:BookingEvent[]; substitutions?:SubstitutionEvent[];
  timeline?:TimelineEvent[]; referees?:any[]; deep_data_available?:boolean
}
export type MatchResponse={configured:boolean;provider:string;source?:string;message?:string;matches:Match[]}
export type Probabilities={home:number;draw:number;away:number;model:string;disclaimer:string}
export type DemoPlayer=Player & {shirt_number:number;role:string;x:number;y:number;rating:number}
export type DemoEvent={minute:number;type:string;team:string;player:string;shirt_number:number;assist?:string|null;text:string;score:string}
export type DemoSnapshot={mode:'demo';generated_at:string;match:Match;lineups:{home:{formation:string;players:DemoPlayer[]};away:{formation:string;players:DemoPlayer[]}};ball:{x:number;y:number};analytics:{xg:{home:number;away:number};possession:{home:number;away:number};shots:{home:number;away:number};shots_on_target:{home:number;away:number};pass_accuracy:{home:number;away:number};corners:{home:number;away:number};pressing_index:{home:number;away:number}};probabilities:Probabilities;analysis:{headline:string;detail:string;confidence:number;generated_by:string};events:DemoEvent[]}
export type StandingRow={position:number;team:Team;played:number;won:number;draw:number;lost:number;gf:number;ga:number;gd:number;points:number}
export type Scorer={player:Player;team:Team;goals:number;assists?:number|null;penalties?:number|null;played_matches?:number|null}
export type Favorite={id:number;entity_type:string;entity_id:string;label:string}

from __future__ import annotations

import json
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    # Club role category: Openers, Middle Order, Spinners, Pacers, Wicket-keeper
    role_group = db.Column(db.String(50), nullable=False)
    specialty = db.Column(db.String(200), nullable=True)
    jersey_number = db.Column(db.Integer, unique=True, nullable=False)
    bio = db.Column(db.Text, nullable=True)


class MatchFixture(db.Model):
    __tablename__ = "match_fixtures"

    id = db.Column(db.Integer, primary_key=True)
    opponent_team = db.Column(db.String(200), nullable=False)
    match_type = db.Column(db.String(50), nullable=False)  # T20, 40-Overs, 50-Overs
    venue = db.Column(db.String(200), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    playing_xi = db.Column(db.Text, nullable=True)  # JSON list of player IDs
    match_status = db.Column(
        db.String(20), nullable=False, default="Upcoming"
    )  # Upcoming, Completed, Abandoned

    def playing_xi_ids(self) -> list[int]:
        if not self.playing_xi:
            return []
        try:
            raw = json.loads(self.playing_xi)
            if isinstance(raw, list):
                return [int(x) for x in raw]
        except Exception:
            return []
        return []

    def set_playing_xi_ids(self, ids: list[int]) -> None:
        self.playing_xi = json.dumps([int(x) for x in ids])


class CricketStat(db.Model):
    __tablename__ = "cricket_stats"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("match_fixtures.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)

    # Batting
    runs_scored = db.Column(db.Integer, nullable=False, default=0)
    balls_faced = db.Column(db.Integer, nullable=False, default=0)
    fours = db.Column(db.Integer, nullable=False, default=0)
    sixes = db.Column(db.Integer, nullable=False, default=0)

    # Bowling
    overs_bowled = db.Column(db.Float, nullable=False, default=0.0)
    wickets_taken = db.Column(db.Integer, nullable=False, default=0)
    runs_conceded = db.Column(db.Integer, nullable=False, default=0)
    maidens = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("match_id", "player_id", name="uq_match_player"),
    )


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin | player
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=True)


def init_db() -> None:
    from werkzeug.security import generate_password_hash

    db.create_all()

    # Seed admin user if missing
    if not User.query.filter_by(username="admin").first():
        db.session.add(
            User(
                username="admin",
                password_hash=generate_password_hash("admin123"),
                role="admin",
                player_id=None,
            )
        )
        db.session.commit()

    # Seed players (top-up to 11 for quick demo)
    desired_seed = [
        Player(
            name="Rohit Sharma (Local)",
            role_group="Openers",
            specialty="Right-hand Bat",
            jersey_number=45,
            bio="Aggressive opener; strong pull and cover drive.",
        ),
        Player(
            name="Virat Kohli (Local)",
            role_group="Middle Order",
            specialty="Right-hand Bat",
            jersey_number=18,
            bio="Chase specialist; anchors the innings.",
        ),
        Player(
            name="Ravindra Jadeja (Local)",
            role_group="Spinners",
            specialty="Left-arm Orthodox",
            jersey_number=8,
            bio="All-rounder; tight lines and quick singles.",
        ),
        Player(
            name="Jasprit Bumrah (Local)",
            role_group="Pacers",
            specialty="Right-arm Fast",
            jersey_number=93,
            bio="Death overs specialist; yorkers and pace variation.",
        ),
        Player(
            name="MS Dhoni (Local)",
            role_group="Wicket-keeper",
            specialty="Keeper",
            jersey_number=7,
            bio="Calm finisher; sharp glove work.",
        ),
        # Additional 6 to make 11
        Player(
            name="Shubman Gill (Local)",
            role_group="Openers",
            specialty="Right-hand Bat",
            jersey_number=77,
            bio="Technically solid opener; good against pace.",
        ),
        Player(
            name="Suryakumar Yadav (Local)",
            role_group="Middle Order",
            specialty="Right-hand Bat",
            jersey_number=63,
            bio="Dynamic middle-order batter; 360° shots.",
        ),
        Player(
            name="Rishabh Pant (Local)",
            role_group="Wicket-keeper",
            specialty="Keeper • Left-hand Bat",
            jersey_number=17,
            bio="Attacking keeper-batter; changes momentum quickly.",
        ),
        Player(
            name="Kuldeep Yadav (Local)",
            role_group="Spinners",
            specialty="Left-arm Chinaman",
            jersey_number=23,
            bio="Wrist-spin option; wicket-taker in middle overs.",
        ),
        Player(
            name="Mohammed Shami (Local)",
            role_group="Pacers",
            specialty="Right-arm Fast",
            jersey_number=11,
            bio="Seam bowler; hits the deck hard.",
        ),
        Player(
            name="Hardik Pandya (Local)",
            role_group="Middle Order",
            specialty="Right-arm Medium-fast • Right-hand Bat",
            jersey_number=33,
            bio="Pace-bowling all-rounder; finishing power.",
        ),
    ]

    existing_jerseys = {j for (j,) in db.session.query(Player.jersey_number).all()}
    to_add = []
    for p in desired_seed:
        if p.jersey_number not in existing_jerseys:
            to_add.append(p)
            existing_jerseys.add(p.jersey_number)
        if Player.query.count() + len(to_add) >= 11:
            break

    if to_add:
        db.session.add_all(to_add)
        db.session.commit()

    # Seed an upcoming fixture if none
    if MatchFixture.query.count() == 0:
        fx = MatchFixture(
            opponent_team="Mumbai Rivals 🏏",
            match_type="T20",
            venue="Shivaji Park Ground",
            date_time=datetime.utcnow(),
            match_status="Upcoming",
        )
        db.session.add(fx)
        db.session.commit()


from __future__ import annotations

import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from models import (
    CricketStat,
    MatchFixture,
    Player,
    User,
    db,
    init_db,
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Ensure Flask instance folder exists (default location for SQLite when using relative paths)
    os.makedirs(app.instance_path, exist_ok=True)

    def _ensure_sqlite_parent_dir(sqlalchemy_uri: str) -> None:
        # Handles common sqlite URI forms:
        # - sqlite:////absolute/path/file.sqlite3
        # - sqlite:///relative.sqlite3
        if not sqlalchemy_uri.startswith("sqlite:"):
            return
        if sqlalchemy_uri in ("sqlite://", "sqlite:///:memory:", "sqlite:///:memory"):
            return

        file_path: str | None = None
        if sqlalchemy_uri.startswith("sqlite:////"):
            # absolute Unix path
            file_path = sqlalchemy_uri.replace("sqlite:////", "/", 1)
        elif sqlalchemy_uri.startswith("sqlite:///"):
            file_path = sqlalchemy_uri.replace("sqlite:///", "", 1)
            if not os.path.isabs(file_path):
                # relative DB file (Flask/SQLAlchemy will place it under instance by default)
                return

        if not file_path:
            return

        parent = os.path.dirname(file_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
    # Database configuration:
    # - If DATABASE_URL is set (e.g. Postgres), we use it.
    # - Else we default to a local SQLite file under /instance (Flask default).
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    else:
        sqlite_path = os.environ.get("SQLITE_PATH", "cricmanage.sqlite3")
        # Relative sqlite path uses Flask's instance folder automatically.
        # Absolute path example (useful on Render with a persistent disk):
        #   sqlite:////var/data/cricmanage.sqlite3
        if sqlite_path.startswith("sqlite:"):
            app.config["SQLALCHEMY_DATABASE_URI"] = sqlite_path
        else:
            app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_path}"
        _ensure_sqlite_parent_dir(app.config["SQLALCHEMY_DATABASE_URI"])
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        init_db()

    def current_user() -> User | None:
        uid = session.get("user_id")
        if not uid:
            return None
        return db.session.get(User, uid)

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user():
                return redirect(url_for("login", next=request.path))
            return fn(*args, **kwargs)

        return wrapper

    def role_required(*roles: str):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                u = current_user()
                if not u:
                    return redirect(url_for("login", next=request.path))
                if u.role not in roles:
                    flash("You do not have access to that page.", "error")
                    return redirect(url_for("index"))
                return fn(*args, **kwargs)

            return wrapper

        return decorator

    @app.context_processor
    def inject_globals():
        return {"current_user": current_user()}

    @app.get("/")
    def index():
        u = current_user()
        if not u:
            return render_template("public_home.html")
        if u.role == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("player_dashboard"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = (request.form.get("username") or "").strip().lower()
            password = request.form.get("password") or ""
            u = User.query.filter_by(username=username).first()
            if not u or not check_password_hash(u.password_hash, password):
                flash("Invalid username or password.", "error")
                return render_template("login.html")
            session["user_id"] = u.id
            flash("Welcome back.", "success")
            nxt = request.args.get("next")
            return redirect(nxt or url_for("index"))
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        flash("Logged out.", "success")
        return redirect(url_for("index"))

    # --------------------------
    # Admin portal
    # --------------------------
    @app.get("/admin")
    @login_required
    @role_required("admin")
    def admin_dashboard():
        upcoming = (
            MatchFixture.query.filter(MatchFixture.match_status == "Upcoming")
            .order_by(MatchFixture.date_time.asc())
            .limit(5)
            .all()
        )
        recent_players = Player.query.order_by(Player.id.desc()).limit(5).all()
        return render_template(
            "admin/dashboard.html", upcoming=upcoming, recent_players=recent_players
        )

    # Players CRUD
    @app.get("/admin/players")
    @login_required
    @role_required("admin")
    def admin_players():
        q = (request.args.get("q") or "").strip()
        players = Player.query
        if q:
            players = players.filter(Player.name.ilike(f"%{q}%"))
        players = players.order_by(Player.jersey_number.asc()).all()
        return render_template("admin/players_list.html", players=players, q=q)

    @app.route("/admin/players/new", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def admin_players_new():
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            role_group = (request.form.get("role_group") or "").strip()
            specialty = (request.form.get("specialty") or "").strip()
            jersey_number = request.form.get("jersey_number")
            bio = (request.form.get("bio") or "").strip()

            if not name or not jersey_number or not role_group:
                flash("Name, Role, and Jersey Number are required.", "error")
                return render_template("admin/player_form.html", player=None)

            try:
                jersey_number_int = int(jersey_number)
            except ValueError:
                flash("Jersey number must be a number.", "error")
                return render_template("admin/player_form.html", player=None)

            if Player.query.filter_by(jersey_number=jersey_number_int).first():
                flash("Jersey number already exists.", "error")
                return render_template("admin/player_form.html", player=None)

            p = Player(
                name=name,
                role_group=role_group,
                specialty=specialty,
                jersey_number=jersey_number_int,
                bio=bio,
            )
            db.session.add(p)
            db.session.commit()
            flash("Player added.", "success")
            return redirect(url_for("admin_players"))

        return render_template("admin/player_form.html", player=None)

    @app.route("/admin/players/<int:player_id>/edit", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def admin_players_edit(player_id: int):
        p = db.session.get(Player, player_id)
        if not p:
            flash("Player not found.", "error")
            return redirect(url_for("admin_players"))

        if request.method == "POST":
            p.name = (request.form.get("name") or "").strip()
            p.role_group = (request.form.get("role_group") or "").strip()
            p.specialty = (request.form.get("specialty") or "").strip()
            p.bio = (request.form.get("bio") or "").strip()

            jersey_number = request.form.get("jersey_number")
            try:
                jersey_number_int = int(jersey_number)
            except Exception:
                flash("Jersey number must be a number.", "error")
                return render_template("admin/player_form.html", player=p)

            existing = Player.query.filter_by(jersey_number=jersey_number_int).first()
            if existing and existing.id != p.id:
                flash("Jersey number already exists.", "error")
                return render_template("admin/player_form.html", player=p)

            p.jersey_number = jersey_number_int
            db.session.commit()
            flash("Player updated.", "success")
            return redirect(url_for("admin_players"))

        return render_template("admin/player_form.html", player=p)

    @app.post("/admin/players/<int:player_id>/delete")
    @login_required
    @role_required("admin")
    def admin_players_delete(player_id: int):
        p = db.session.get(Player, player_id)
        if not p:
            flash("Player not found.", "error")
            return redirect(url_for("admin_players"))
        db.session.delete(p)
        db.session.commit()
        flash("Player deleted.", "success")
        return redirect(url_for("admin_players"))

    # Fixtures
    @app.get("/admin/fixtures")
    @login_required
    @role_required("admin")
    def admin_fixtures():
        fixtures = MatchFixture.query.order_by(MatchFixture.date_time.desc()).all()
        return render_template("admin/fixtures_list.html", fixtures=fixtures)

    @app.route("/admin/fixtures/new", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def admin_fixtures_new():
        if request.method == "POST":
            opponent_team = (request.form.get("opponent_team") or "").strip()
            match_type = (request.form.get("match_type") or "").strip()
            venue = (request.form.get("venue") or "").strip()
            date_time_raw = (request.form.get("date_time") or "").strip()

            if not opponent_team or not match_type or not venue or not date_time_raw:
                flash("All fields are required.", "error")
                return render_template("admin/fixture_form.html", fixture=None)

            try:
                dt = datetime.fromisoformat(date_time_raw)
            except ValueError:
                flash("Invalid date/time.", "error")
                return render_template("admin/fixture_form.html", fixture=None)

            f = MatchFixture(
                opponent_team=opponent_team,
                match_type=match_type,
                venue=venue,
                date_time=dt,
                match_status="Upcoming",
            )
            db.session.add(f)
            db.session.commit()
            flash("Fixture created.", "success")
            return redirect(url_for("admin_fixtures"))

        return render_template("admin/fixture_form.html", fixture=None)

    @app.route("/admin/fixtures/<int:fixture_id>/edit", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def admin_fixtures_edit(fixture_id: int):
        f = db.session.get(MatchFixture, fixture_id)
        if not f:
            flash("Fixture not found.", "error")
            return redirect(url_for("admin_fixtures"))

        if request.method == "POST":
            f.opponent_team = (request.form.get("opponent_team") or "").strip()
            f.match_type = (request.form.get("match_type") or "").strip()
            f.venue = (request.form.get("venue") or "").strip()
            date_time_raw = (request.form.get("date_time") or "").strip()
            f.match_status = (request.form.get("match_status") or "").strip()

            try:
                f.date_time = datetime.fromisoformat(date_time_raw)
            except ValueError:
                flash("Invalid date/time.", "error")
                return render_template("admin/fixture_form.html", fixture=f)

            db.session.commit()
            flash("Fixture updated.", "success")
            return redirect(url_for("admin_fixtures"))

        return render_template("admin/fixture_form.html", fixture=f)

    # Playing XI builder
    @app.route("/admin/fixtures/<int:fixture_id>/playing-xi", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def admin_fixture_playing_xi(fixture_id: int):
        fixture = db.session.get(MatchFixture, fixture_id)
        if not fixture:
            flash("Fixture not found.", "error")
            return redirect(url_for("admin_fixtures"))

        players = Player.query.order_by(Player.role_group.asc(), Player.jersey_number.asc()).all()
        selected_ids = set(fixture.playing_xi_ids())

        if request.method == "POST":
            chosen = request.form.getlist("playing_xi")
            try:
                chosen_ids = [int(x) for x in chosen]
            except Exception:
                flash("Invalid selection.", "error")
                return redirect(url_for("admin_fixture_playing_xi", fixture_id=fixture_id))

            if len(chosen_ids) != 11:
                flash("Playing XI must be exactly 11 players.", "error")
                selected_ids = set(chosen_ids)
                return render_template(
                    "admin/playing_xi.html",
                    fixture=fixture,
                    players=players,
                    selected_ids=selected_ids,
                )

            fixture.set_playing_xi_ids(chosen_ids)
            db.session.commit()
            flash("Playing XI saved.", "success")
            return redirect(url_for("admin_fixtures"))

        return render_template(
            "admin/playing_xi.html",
            fixture=fixture,
            players=players,
            selected_ids=selected_ids,
        )

    # Post-match scoring
    @app.route("/admin/fixtures/<int:fixture_id>/scorecard", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def admin_fixture_scorecard(fixture_id: int):
        fixture = db.session.get(MatchFixture, fixture_id)
        if not fixture:
            flash("Fixture not found.", "error")
            return redirect(url_for("admin_fixtures"))

        xi_ids = fixture.playing_xi_ids()
        players = []
        if xi_ids:
            players = Player.query.filter(Player.id.in_(xi_ids)).all()
            players.sort(key=lambda p: xi_ids.index(p.id))

        if request.method == "POST":
            if fixture.match_status != "Completed":
                fixture.match_status = "Completed"

            for p in players:
                runs = int(request.form.get(f"runs_{p.id}") or 0)
                balls = int(request.form.get(f"balls_{p.id}") or 0)
                fours = int(request.form.get(f"fours_{p.id}") or 0)
                sixes = int(request.form.get(f"sixes_{p.id}") or 0)

                overs = float(request.form.get(f"overs_{p.id}") or 0)
                wkts = int(request.form.get(f"wkts_{p.id}") or 0)
                conceded = int(request.form.get(f"conceded_{p.id}") or 0)
                maidens = int(request.form.get(f"maidens_{p.id}") or 0)

                stat = CricketStat.query.filter_by(match_id=fixture.id, player_id=p.id).first()
                if not stat:
                    stat = CricketStat(match_id=fixture.id, player_id=p.id)
                    db.session.add(stat)

                stat.runs_scored = runs
                stat.balls_faced = balls
                stat.fours = fours
                stat.sixes = sixes

                stat.overs_bowled = overs
                stat.wickets_taken = wkts
                stat.runs_conceded = conceded
                stat.maidens = maidens

            db.session.commit()
            flash("Scorecard saved.", "success")
            return redirect(url_for("admin_fixtures"))

        existing = {
            s.player_id: s
            for s in CricketStat.query.filter_by(match_id=fixture.id).all()
        }
        return render_template(
            "admin/scorecard.html",
            fixture=fixture,
            players=players,
            existing=existing,
        )

    # Create player login
    @app.route("/admin/players/<int:player_id>/create-login", methods=["POST"])
    @login_required
    @role_required("admin")
    def admin_create_player_login(player_id: int):
        p = db.session.get(Player, player_id)
        if not p:
            flash("Player not found.", "error")
            return redirect(url_for("admin_players"))

        username = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""
        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("admin_players_edit", player_id=player_id))

        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "error")
            return redirect(url_for("admin_players_edit", player_id=player_id))

        u = User(
            username=username,
            password_hash=generate_password_hash(password),
            role="player",
            player_id=p.id,
        )
        db.session.add(u)
        db.session.commit()
        flash("Player login created.", "success")
        return redirect(url_for("admin_players_edit", player_id=player_id))

    # --------------------------
    # Player portal
    # --------------------------
    @app.get("/player")
    @login_required
    @role_required("player")
    def player_dashboard():
        u = current_user()
        assert u is not None
        if not u.player_id:
            flash("Your account is not linked to a player profile.", "error")
            return redirect(url_for("logout"))

        player = db.session.get(Player, u.player_id)
        if not player:
            flash("Player profile missing.", "error")
            return redirect(url_for("logout"))

        # Career totals & recent form
        stats = (
            CricketStat.query.join(MatchFixture, CricketStat.match_id == MatchFixture.id)
            .filter(CricketStat.player_id == player.id)
            .filter(MatchFixture.match_status == "Completed")
            .order_by(MatchFixture.date_time.asc())
            .all()
        )

        career_runs = sum(s.runs_scored for s in stats)
        career_wkts = sum(s.wickets_taken for s in stats)
        innings = len([s for s in stats if s.balls_faced is not None])

        recent = stats[-5:] if len(stats) > 5 else stats
        recent_runs = [s.runs_scored for s in recent]
        recent_wkts = [s.wickets_taken for s in recent]

        # Upcoming lineup reminder
        next_match = (
            MatchFixture.query.filter(MatchFixture.match_status == "Upcoming")
            .order_by(MatchFixture.date_time.asc())
            .first()
        )
        in_xi = False
        if next_match:
            in_xi = player.id in next_match.playing_xi_ids()

        return render_template(
            "player/dashboard.html",
            player=player,
            career_runs=career_runs,
            career_wkts=career_wkts,
            innings=innings,
            stats=stats,
            recent_runs=recent_runs,
            recent_wkts=recent_wkts,
            next_match=next_match,
            in_xi=in_xi,
        )

    @app.get("/player/squad")
    @login_required
    @role_required("player")
    def player_squad():
        players = Player.query.order_by(Player.jersey_number.asc()).all()
        return render_template("player/squad.html", players=players)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(debug=True, host="127.0.0.1", port=port)


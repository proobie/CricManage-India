# CricManage India — Project Documentation

## 1) Project Overview

**CricManage India** is a digital management system built for **Indian cricket clubs & academies**. It helps a club manage:

- Player roster (roles, specialties, jersey numbers, bio)
- Match fixtures (opponent, venue/ground, type, scheduled date/time)
- “Playing XI” selection for upcoming matches
- Post-match score logging (batting + bowling)
- A Player Portal showing career totals, form trends, and a Starting XI reminder

This project was designed as a **final year web application** with a clean UI, role-based portals, and a cricket-specific database.

---

## 2) Tech Stack Used

### Frontend
- **HTML5** templates (Jinja2 via Flask)
- **Tailwind CSS** (CDN) for responsive UI
- **Chart.js** (CDN) for player analytics charts

### Backend
- **Python + Flask**
  - Routing, views, sessions
  - Role-based access control (Admin vs Player)

### Database
- **SQLite** using **Flask-SQLAlchemy**
  - Local-first cricket data storage
  - Works well for club-level deployments and demos

### Deployment (optional)
- **Render.com** (supports Python web apps)
- Production server via **Waitress** (cross-platform WSGI server)

---

## 3) User Roles & Features

### A) Admin Portal (Coach / Manager)
- **Squad management**
  - Add/edit/delete players
  - Assign role group: Openers / Middle Order / Spinners / Pacers / Wicket-keeper
  - Store specialty (e.g., Right-arm Off-break) and jersey number
- **Fixture scheduler**
  - Add fixtures with opponent, match type (T20 / 40-Overs / 50-Overs), venue, date/time
  - Track match status: Upcoming / Completed / Abandoned
- **Playing XI Builder**
  - Select **exactly 11** players for a fixture
  - Stored against the fixture and shown across portals
- **Post-match scorecard**
  - Batting: runs, balls, fours, sixes
  - Bowling: overs, wickets, runs conceded, maidens
  - Saving scorecard marks match as **Completed**
- **Create Player login**
  - Admin can generate a Player Portal account linked to a player

### B) Player Portal (Athlete)
- **Profile dashboard**
  - Career totals (runs + wickets)
  - Match-by-match stats list (completed matches)
- **Performance analytics**
  - Runs per match (line chart)
  - Wickets per match (bar chart)
- **Lineup reminder**
  - Shows upcoming match and whether the player is in the **Starting XI**
- **Squad view**
  - View teammates with roles and specialties

---

## 4) Database Schema

### `players`
- `id` (PK)
- `name`
- `role_group` (Openers, Middle Order, Spinners, Pacers, Wicket-keeper)
- `specialty`
- `jersey_number` (unique)
- `bio`

### `match_fixtures`
- `id` (PK)
- `opponent_team`
- `match_type` (T20, 40-Overs, 50-Overs)
- `venue`
- `date_time`
- `playing_xi` (JSON list of 11 player IDs)
- `match_status` (Upcoming, Completed, Abandoned)

### `cricket_stats`
- `id` (PK)
- `match_id` (FK → `match_fixtures.id`)
- `player_id` (FK → `players.id`)
- Batting: `runs_scored`, `balls_faced`, `fours`, `sixes`
- Bowling: `overs_bowled`, `wickets_taken`, `runs_conceded`, `maidens`
- Unique constraint: (`match_id`, `player_id`)

### `users` (authentication)
- `id` (PK)
- `username` (unique)
- `password_hash`
- `role` (`admin` or `player`)
- `player_id` (nullable FK to `players`)

---

## 5) Application Structure

Typical layout:

- `app.py`: Flask app factory + routes (Admin + Player)
- `models.py`: SQLAlchemy models and DB seeding
- `templates/`: UI templates (Tailwind + Jinja)
  - `templates/admin/*`
  - `templates/player/*`

SQLite DB lives in:
- `instance/cricmanage.sqlite3`

---

## 6) Key Pages / Routes

### Public
- `/` home
- `/login` login form
- `/logout` logout (POST)

### Admin
- `/admin` dashboard
- `/admin/players` squad list
- `/admin/players/new` add player
- `/admin/players/<id>/edit` edit player + create login
- `/admin/fixtures` fixtures list
- `/admin/fixtures/new` create fixture
- `/admin/fixtures/<id>/edit` edit fixture
- `/admin/fixtures/<id>/playing-xi` playing XI builder
- `/admin/fixtures/<id>/scorecard` score entry

### Player
- `/player` dashboard + analytics
- `/player/squad` squad view

---

## 7) UI/UX Theme Notes (Indian Cricket)

- **Colors**
  - Cricket Green: `#064e3b`
  - Premium Gold: `#fbbf24`
- **Typography**
  - Poppins for bold, energetic feel
- **Mobile responsiveness**
  - Mobile dropdown menu
  - Tables remain scrollable with tighter spacing
  - Playing XI layout stacks on mobile

---

## 8) Security Notes (Academic project)

- Passwords are stored as **hashed** values (`werkzeug.security`)
- Authentication uses **Flask sessions**
- Admin and Player pages are protected via role checks

---

## 9) Future Improvements (Optional)

- Role-based selection suggestions (auto-balance XI)
- Export scorecards as PDF
- Player self-service password reset
- Team logo uploads instead of emojis
- Move from SQLite → Postgres for multi-user production


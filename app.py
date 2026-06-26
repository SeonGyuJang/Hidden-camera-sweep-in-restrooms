import os
import base64
import json
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, jsonify, flash, send_file
)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import io

load_dotenv()

app = Flask(__name__)

database_url = os.environ.get("DATABASE_URL", "sqlite:///inspection.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ── Team definitions (static config) ─────────────────────────────────────────

TEAMS = {
    "A": {
        "name": "도보A팀",
        "type": "도보",
        "color": "#3B82F6",
        "members": ["오미령", "문재준"],
        "partners": ["디지털성폭력지원센터"],
        "buildings": ["신정문 주차장", "학술정보원", "농심국제관"],
    },
    "B": {
        "name": "도보B팀",
        "type": "도보",
        "color": "#10B981",
        "members": ["김종욱", "정승훈", "백서영"],
        "partners": ["디지털성폭력지원센터"],
        "buildings": ["공공정책관", "과학기술2관", "호연학사(미래관 1층)"],
    },
    "C": {
        "name": "차량C팀",
        "type": "차량",
        "color": "#F59E0B",
        "members": ["서홍욱", "민서현"],
        "partners": ["세종북부경찰서"],
        "buildings": ["산학협력관", "과학기술1관", "가속기ICT융합관"],
    },
    "D": {
        "name": "차량D팀",
        "type": "차량",
        "color": "#8B5CF6",
        "members": ["장선규", "김바다"],
        "partners": ["세종북부경찰서"],
        "buildings": ["학생회관", "석원경상관", "문화스포츠관"],
    },
}

BUILDINGS_SEED = [
    # 팀A
    {"name": "신정문 주차장",      "team": "A", "lat": 36.5972, "lng": 127.2855},
    {"name": "학술정보원",         "team": "A", "lat": 36.6002, "lng": 127.2878},
    {"name": "농심국제관",         "team": "A", "lat": 36.6018, "lng": 127.2898},
    # 팀B
    {"name": "공공정책관",         "team": "B", "lat": 36.5995, "lng": 127.2862},
    {"name": "과학기술2관",        "team": "B", "lat": 36.5982, "lng": 127.2848},
    {"name": "호연학사(미래관 1층)","team": "B", "lat": 36.5965, "lng": 127.2872},
    # 팀C
    {"name": "산학협력관",         "team": "C", "lat": 36.5990, "lng": 127.2905},
    {"name": "과학기술1관",        "team": "C", "lat": 36.5978, "lng": 127.2870},
    {"name": "가속기ICT융합관",    "team": "C", "lat": 36.5962, "lng": 127.2845},
    # 팀D
    {"name": "학생회관",           "team": "D", "lat": 36.5988, "lng": 127.2892},
    {"name": "석원경상관",         "team": "D", "lat": 36.6008, "lng": 127.2908},
    {"name": "문화스포츠관",       "team": "D", "lat": 36.5952, "lng": 127.2888},
]


# ── Models ────────────────────────────────────────────────────────────────────

class Building(db.Model):
    __tablename__ = "buildings"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    team = db.Column(db.String(2), nullable=False)   # A/B/C/D
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    restrooms = db.relationship("Restroom", backref="building", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "team": self.team,
            "lat": self.lat,
            "lng": self.lng,
            "color": TEAMS[self.team]["color"],
            "restroom_count": len(self.restrooms),
        }


class Restroom(db.Model):
    __tablename__ = "restrooms"
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey("buildings.id"), nullable=False)
    floor = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # 남/여/공용
    location_detail = db.Column(db.String(200))
    inspections = db.relationship("Inspection", backref="restroom", lazy=True, cascade="all, delete-orphan")

    @property
    def label(self):
        return f"{self.building.name} {self.floor} {self.gender}화장실"

    def to_dict(self):
        completed = any(i.completed for i in self.inspections)
        return {
            "id": self.id,
            "building_id": self.building_id,
            "building_name": self.building.name,
            "floor": self.floor,
            "gender": self.gender,
            "location_detail": self.location_detail or "",
            "completed": completed,
            "team": self.building.team,
        }


class Inspection(db.Model):
    __tablename__ = "inspections"
    id = db.Column(db.Integer, primary_key=True)
    restroom_id = db.Column(db.Integer, db.ForeignKey("restrooms.id"), nullable=False)
    team = db.Column(db.String(2), nullable=False)         # A/B/C/D
    inspector_name = db.Column(db.String(100))
    before_photo = db.Column(db.Text)
    after_photo = db.Column(db.Text)
    # GPS where photo was taken
    photo_lat = db.Column(db.Float)
    photo_lng = db.Column(db.Float)
    action_taken = db.Column(db.Boolean, default=False)
    action_detail = db.Column(db.Text)
    notes = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "restroom_id": self.restroom_id,
            "restroom_label": self.restroom.label,
            "building_name": self.restroom.building.name,
            "floor": self.restroom.floor,
            "gender": self.restroom.gender,
            "team": self.team,
            "team_name": TEAMS.get(self.team, {}).get("name", self.team),
            "inspector_name": self.inspector_name or "",
            "action_taken": self.action_taken,
            "action_detail": self.action_detail or "",
            "notes": self.notes or "",
            "completed": self.completed,
            "has_before_photo": bool(self.before_photo),
            "has_after_photo": bool(self.after_photo),
            "photo_lat": self.photo_lat,
            "photo_lng": self.photo_lng,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
        }


# ── Seed ──────────────────────────────────────────────────────────────────────

def seed_buildings():
    if Building.query.count() == 0:
        for b in BUILDINGS_SEED:
            db.session.add(Building(**b))
        db.session.commit()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    buildings = Building.query.all()
    total = Restroom.query.count()
    done = db.session.query(Restroom.id).join(Inspection).filter(Inspection.completed == True).distinct().count()
    inspections = Inspection.query.count()
    team_stats = {}
    for tid in TEAMS:
        t_total = Inspection.query.filter_by(team=tid).count()
        t_done = Inspection.query.filter_by(team=tid, completed=True).count()
        team_stats[tid] = {"total": t_total, "done": t_done}
    return render_template(
        "index.html",
        teams=TEAMS,
        buildings=buildings,
        total_restrooms=total,
        completed_restrooms=done,
        total_inspections=inspections,
        team_stats=team_stats,
        buildings_json=json.dumps([b.to_dict() for b in buildings]),
        teams_json=json.dumps(TEAMS),
    )


# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/buildings")
def api_buildings():
    return jsonify([b.to_dict() for b in Building.query.all()])


@app.route("/api/buildings/<int:bid>/restrooms")
def api_building_restrooms(bid):
    building = Building.query.get_or_404(bid)
    return jsonify([r.to_dict() for r in building.restrooms])


@app.route("/api/team/<team>/restrooms")
def api_team_restrooms(team):
    buildings = Building.query.filter_by(team=team).all()
    result = []
    for b in buildings:
        for r in b.restrooms:
            result.append(r.to_dict())
    return jsonify(result)


# ── Restroom ──────────────────────────────────────────────────────────────────

@app.route("/restrooms")
def restrooms():
    team = request.args.get("team")
    gender = request.args.get("gender")
    query = Restroom.query.join(Building)
    if team:
        query = query.filter(Building.team == team)
    if gender:
        query = query.filter(Restroom.gender == gender)
    items = query.order_by(Building.team, Building.name, Restroom.floor).all()
    return render_template("restrooms.html", items=items, teams=TEAMS,
                           sel_team=team, sel_gender=gender)


@app.route("/restrooms/new", methods=["GET", "POST"])
def restroom_new():
    buildings = Building.query.order_by(Building.team, Building.name).all()
    prefill_building = request.args.get("building_id", type=int)
    if request.method == "POST":
        r = Restroom(
            building_id=request.form["building_id"],
            floor=request.form["floor"],
            gender=request.form["gender"],
            location_detail=request.form.get("location_detail", ""),
        )
        db.session.add(r)
        db.session.commit()
        flash("화장실이 등록되었습니다.", "success")
        return redirect(url_for("restrooms"))
    return render_template("restroom_new.html", buildings=buildings, prefill_building=prefill_building)


@app.route("/restrooms/<int:rid>/delete", methods=["POST"])
def restroom_delete(rid):
    r = Restroom.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    flash("삭제되었습니다.", "info")
    return redirect(url_for("restrooms"))


# ── Inspection ────────────────────────────────────────────────────────────────

@app.route("/report", methods=["GET", "POST"])
def report():
    """Mobile-first report form."""
    buildings = Building.query.order_by(Building.team, Building.name).all()
    prefill_building = request.args.get("building_id", type=int)
    prefill_restroom = request.args.get("restroom_id", type=int)
    if request.method == "POST":
        lat = request.form.get("photo_lat") or None
        lng = request.form.get("photo_lng") or None
        insp = Inspection(
            restroom_id=request.form["restroom_id"],
            team=request.form["team"],
            inspector_name=request.form.get("inspector_name", ""),
            before_photo=request.form.get("before_photo") or None,
            after_photo=request.form.get("after_photo") or None,
            photo_lat=float(lat) if lat else None,
            photo_lng=float(lng) if lng else None,
            action_taken=bool(request.form.get("action_taken")),
            action_detail=request.form.get("action_detail", ""),
            notes=request.form.get("notes", ""),
            completed=bool(request.form.get("completed")),
        )
        db.session.add(insp)
        db.session.commit()
        flash("점검 기록이 저장되었습니다.", "success")
        return redirect(url_for("report_done", iid=insp.id))
    restrooms = Restroom.query.join(Building).order_by(Building.team, Building.name, Restroom.floor).all()
    return render_template("report.html", buildings=buildings, restrooms=restrooms,
                           teams=TEAMS, prefill_building=prefill_building,
                           prefill_restroom=prefill_restroom)


@app.route("/report/done/<int:iid>")
def report_done(iid):
    insp = Inspection.query.get_or_404(iid)
    return render_template("report_done.html", insp=insp, teams=TEAMS)


@app.route("/records")
def records():
    team = request.args.get("team")
    query = Inspection.query.join(Restroom).join(Building)
    if team:
        query = query.filter(Inspection.team == team)
    items = query.order_by(Inspection.created_at.desc()).all()
    return render_template("records.html", items=items, teams=TEAMS, sel_team=team)


@app.route("/records/<int:iid>")
def record_detail(iid):
    insp = Inspection.query.get_or_404(iid)
    return render_template("record_detail.html", insp=insp, teams=TEAMS)


@app.route("/records/<int:iid>/edit", methods=["GET", "POST"])
def record_edit(iid):
    insp = Inspection.query.get_or_404(iid)
    restrooms = Restroom.query.join(Building).order_by(Building.team, Building.name, Restroom.floor).all()
    if request.method == "POST":
        insp.restroom_id = request.form["restroom_id"]
        insp.team = request.form["team"]
        insp.inspector_name = request.form.get("inspector_name", "")
        if request.form.get("before_photo"):
            insp.before_photo = request.form["before_photo"]
        if request.form.get("after_photo"):
            insp.after_photo = request.form["after_photo"]
        lat = request.form.get("photo_lat") or None
        lng = request.form.get("photo_lng") or None
        if lat:
            insp.photo_lat = float(lat)
        if lng:
            insp.photo_lng = float(lng)
        insp.action_taken = bool(request.form.get("action_taken"))
        insp.action_detail = request.form.get("action_detail", "")
        insp.notes = request.form.get("notes", "")
        insp.completed = bool(request.form.get("completed"))
        insp.updated_at = datetime.utcnow()
        db.session.commit()
        flash("수정되었습니다.", "success")
        return redirect(url_for("record_detail", iid=insp.id))
    buildings = Building.query.order_by(Building.team, Building.name).all()
    return render_template("record_edit.html", insp=insp, restrooms=restrooms,
                           buildings=buildings, teams=TEAMS)


@app.route("/records/<int:iid>/delete", methods=["POST"])
def record_delete(iid):
    insp = Inspection.query.get_or_404(iid)
    db.session.delete(insp)
    db.session.commit()
    flash("삭제되었습니다.", "info")
    return redirect(url_for("records"))


@app.route("/records/<int:iid>/photo/<which>")
def record_photo(iid, which):
    insp = Inspection.query.get_or_404(iid)
    data_url = insp.before_photo if which == "before" else insp.after_photo
    if not data_url:
        return "사진 없음", 404
    header, encoded = data_url.split(",", 1)
    mime = header.split(":")[1].split(";")[0]
    img_bytes = base64.b64decode(encoded)
    return send_file(io.BytesIO(img_bytes), mimetype=mime,
                     download_name=f"inspection_{iid}_{which}.jpg")


# ── Summary ───────────────────────────────────────────────────────────────────

@app.route("/summary")
def summary():
    buildings = Building.query.order_by(Building.team, Building.name).all()
    team_stats = {}
    for tid, tdata in TEAMS.items():
        bids = [b.id for b in Building.query.filter_by(team=tid).all()]
        rids = [r.id for b in Building.query.filter_by(team=tid).all() for r in b.restrooms]
        total_r = len(rids)
        done_r = 0
        for rid in rids:
            if Inspection.query.filter_by(restroom_id=rid, completed=True).first():
                done_r += 1
        total_i = Inspection.query.filter_by(team=tid).count()
        actions = Inspection.query.filter_by(team=tid, action_taken=True).count()
        team_stats[tid] = {
            "total_restrooms": total_r,
            "done_restrooms": done_r,
            "total_inspections": total_i,
            "actions": actions,
        }
    all_inspections = Inspection.query.order_by(Inspection.created_at.desc()).limit(20).all()
    return render_template("summary.html", buildings=buildings, teams=TEAMS,
                           team_stats=team_stats, recent=all_inspections)


@app.route("/api/export")
def api_export():
    return jsonify([i.to_dict() for i in Inspection.query.all()])


# ── CLI ───────────────────────────────────────────────────────────────────────

@app.cli.command("init-db")
def init_db():
    db.create_all()
    seed_buildings()
    print("Done.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_buildings()
    app.run(debug=True, host="0.0.0.0", port=5000)

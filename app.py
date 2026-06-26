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

# ── Database ──────────────────────────────────────────────────────────────────
database_url = os.environ.get("DATABASE_URL", "sqlite:///inspection.db")
# fly.io postgres uses postgres:// prefix; SQLAlchemy needs postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ── Models ────────────────────────────────────────────────────────────────────

class Building(db.Model):
    __tablename__ = "buildings"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100))
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    restrooms = db.relationship("Restroom", backref="building", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "name_en": self.name_en or "",
            "lat": self.lat,
            "lng": self.lng,
            "restroom_count": len(self.restrooms),
        }


class Restroom(db.Model):
    __tablename__ = "restrooms"
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey("buildings.id"), nullable=False)
    floor = db.Column(db.String(20), nullable=False)          # e.g. "1F", "B1"
    gender = db.Column(db.String(10), nullable=False)         # 남/여/공용
    location_detail = db.Column(db.String(200))
    inspections = db.relationship("Inspection", backref="restroom", lazy=True, cascade="all, delete-orphan")

    @property
    def label(self):
        return f"{self.building.name} {self.floor} {self.gender}화장실"

    def to_dict(self):
        done = any(i.completed for i in self.inspections)
        return {
            "id": self.id,
            "building_id": self.building_id,
            "building_name": self.building.name,
            "floor": self.floor,
            "gender": self.gender,
            "location_detail": self.location_detail or "",
            "completed": done,
            "inspection_count": len(self.inspections),
        }


class Inspection(db.Model):
    __tablename__ = "inspections"
    id = db.Column(db.Integer, primary_key=True)
    restroom_id = db.Column(db.Integer, db.ForeignKey("restrooms.id"), nullable=False)
    group_number = db.Column(db.Integer, nullable=False)      # 1~4조
    inspector_name = db.Column(db.String(100))
    before_photo = db.Column(db.Text)   # base64 data-url
    after_photo = db.Column(db.Text)    # base64 data-url
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
            "group_number": self.group_number,
            "inspector_name": self.inspector_name or "",
            "action_taken": self.action_taken,
            "action_detail": self.action_detail or "",
            "notes": self.notes or "",
            "completed": self.completed,
            "has_before_photo": bool(self.before_photo),
            "has_after_photo": bool(self.after_photo),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
        }


# ── Seed data ─────────────────────────────────────────────────────────────────

BUILDINGS_SEED = [
    {"name": "학술정보관",       "name_en": "Library",               "lat": 36.60002, "lng": 127.28798},
    {"name": "공학관",          "name_en": "Engineering Hall",       "lat": 36.59921, "lng": 127.28651},
    {"name": "과학관",          "name_en": "Science Hall",           "lat": 36.59975, "lng": 127.28547},
    {"name": "인문사회관",       "name_en": "Humanities Hall",        "lat": 36.60081, "lng": 127.28712},
    {"name": "경상관",          "name_en": "Business Hall",          "lat": 36.60055, "lng": 127.28880},
    {"name": "학생회관",         "name_en": "Student Union",          "lat": 36.59868, "lng": 127.28820},
    {"name": "체육관",          "name_en": "Gymnasium",              "lat": 36.59800, "lng": 127.28700},
    {"name": "생명과학관",       "name_en": "Life Science Hall",      "lat": 36.60030, "lng": 127.28450},
    {"name": "미디어관",         "name_en": "Media Hall",             "lat": 36.60120, "lng": 127.28600},
    {"name": "국제관",          "name_en": "International Hall",     "lat": 36.60160, "lng": 127.28850},
    {"name": "본관",            "name_en": "Main Building",          "lat": 36.60100, "lng": 127.28750},
    {"name": "산학협력관",       "name_en": "Industry Cooperation",   "lat": 36.59950, "lng": 127.28900},
    {"name": "기숙사(화봉관)",   "name_en": "Hwabong Dormitory",      "lat": 36.59700, "lng": 127.28600},
    {"name": "기숙사(세화관)",   "name_en": "Sehwa Dormitory",        "lat": 36.59650, "lng": 127.28750},
    {"name": "창업보육센터",     "name_en": "Business Incubator",     "lat": 36.59880, "lng": 127.29000},
]


def seed_buildings():
    if Building.query.count() == 0:
        for b in BUILDINGS_SEED:
            db.session.add(Building(**b))
        db.session.commit()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    buildings = Building.query.all()
    total_restrooms = Restroom.query.count()
    completed_restrooms = Restroom.query.join(Inspection).filter(Inspection.completed == True).distinct().count()
    total_inspections = Inspection.query.count()
    return render_template(
        "index.html",
        buildings=buildings,
        total_restrooms=total_restrooms,
        completed_restrooms=completed_restrooms,
        total_inspections=total_inspections,
        buildings_json=json.dumps([b.to_dict() for b in buildings]),
    )


# ── Building API ──────────────────────────────────────────────────────────────

@app.route("/api/buildings")
def api_buildings():
    return jsonify([b.to_dict() for b in Building.query.all()])


@app.route("/api/buildings/<int:bid>/restrooms")
def api_building_restrooms(bid):
    building = Building.query.get_or_404(bid)
    return jsonify([r.to_dict() for r in building.restrooms])


# ── Restroom routes ───────────────────────────────────────────────────────────

@app.route("/restrooms")
def restrooms():
    building_id = request.args.get("building_id", type=int)
    gender = request.args.get("gender")
    query = Restroom.query.join(Building)
    if building_id:
        query = query.filter(Restroom.building_id == building_id)
    if gender:
        query = query.filter(Restroom.gender == gender)
    restrooms = query.order_by(Building.name, Restroom.floor).all()
    buildings = Building.query.order_by(Building.name).all()
    return render_template("restrooms.html", restrooms=restrooms, buildings=buildings,
                           sel_building=building_id, sel_gender=gender)


@app.route("/restrooms/new", methods=["GET", "POST"])
def restroom_new():
    buildings = Building.query.order_by(Building.name).all()
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
    return render_template("restroom_new.html", buildings=buildings)


@app.route("/restrooms/<int:rid>/delete", methods=["POST"])
def restroom_delete(rid):
    r = Restroom.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    flash("화장실 정보가 삭제되었습니다.", "info")
    return redirect(url_for("restrooms"))


# ── Inspection routes ─────────────────────────────────────────────────────────

@app.route("/inspections")
def inspections():
    group = request.args.get("group", type=int)
    completed = request.args.get("completed")
    query = Inspection.query.join(Restroom).join(Building)
    if group:
        query = query.filter(Inspection.group_number == group)
    if completed == "1":
        query = query.filter(Inspection.completed == True)
    elif completed == "0":
        query = query.filter(Inspection.completed == False)
    items = query.order_by(Inspection.created_at.desc()).all()
    return render_template("inspections.html", items=items, sel_group=group, sel_completed=completed)


@app.route("/inspections/new", methods=["GET", "POST"])
def inspection_new():
    buildings = Building.query.order_by(Building.name).all()
    prefill_restroom = request.args.get("restroom_id", type=int)
    if request.method == "POST":
        insp = Inspection(
            restroom_id=request.form["restroom_id"],
            group_number=request.form["group_number"],
            inspector_name=request.form.get("inspector_name", ""),
            before_photo=request.form.get("before_photo") or None,
            after_photo=request.form.get("after_photo") or None,
            action_taken=bool(request.form.get("action_taken")),
            action_detail=request.form.get("action_detail", ""),
            notes=request.form.get("notes", ""),
            completed=bool(request.form.get("completed")),
        )
        db.session.add(insp)
        db.session.commit()
        flash("점검 기록이 저장되었습니다.", "success")
        return redirect(url_for("inspection_detail", iid=insp.id))
    restrooms = Restroom.query.join(Building).order_by(Building.name, Restroom.floor).all()
    return render_template("inspection_new.html", buildings=buildings,
                           restrooms=restrooms, prefill_restroom=prefill_restroom)


@app.route("/inspections/<int:iid>")
def inspection_detail(iid):
    insp = Inspection.query.get_or_404(iid)
    return render_template("inspection_detail.html", insp=insp)


@app.route("/inspections/<int:iid>/edit", methods=["GET", "POST"])
def inspection_edit(iid):
    insp = Inspection.query.get_or_404(iid)
    restrooms = Restroom.query.join(Building).order_by(Building.name, Restroom.floor).all()
    if request.method == "POST":
        insp.restroom_id = request.form["restroom_id"]
        insp.group_number = request.form["group_number"]
        insp.inspector_name = request.form.get("inspector_name", "")
        if request.form.get("before_photo"):
            insp.before_photo = request.form["before_photo"]
        if request.form.get("after_photo"):
            insp.after_photo = request.form["after_photo"]
        insp.action_taken = bool(request.form.get("action_taken"))
        insp.action_detail = request.form.get("action_detail", "")
        insp.notes = request.form.get("notes", "")
        insp.completed = bool(request.form.get("completed"))
        insp.updated_at = datetime.utcnow()
        db.session.commit()
        flash("점검 기록이 수정되었습니다.", "success")
        return redirect(url_for("inspection_detail", iid=insp.id))
    return render_template("inspection_edit.html", insp=insp, restrooms=restrooms)


@app.route("/inspections/<int:iid>/delete", methods=["POST"])
def inspection_delete(iid):
    insp = Inspection.query.get_or_404(iid)
    db.session.delete(insp)
    db.session.commit()
    flash("점검 기록이 삭제되었습니다.", "info")
    return redirect(url_for("inspections"))


# ── Photo endpoint (download) ─────────────────────────────────────────────────

@app.route("/inspections/<int:iid>/photo/<which>")
def inspection_photo(iid, which):
    insp = Inspection.query.get_or_404(iid)
    data_url = insp.before_photo if which == "before" else insp.after_photo
    if not data_url:
        return "사진 없음", 404
    header, encoded = data_url.split(",", 1)
    mime = header.split(":")[1].split(";")[0]
    img_bytes = base64.b64decode(encoded)
    return send_file(io.BytesIO(img_bytes), mimetype=mime,
                     download_name=f"inspection_{iid}_{which}.jpg")


# ── Summary / export ──────────────────────────────────────────────────────────

@app.route("/summary")
def summary():
    buildings = Building.query.order_by(Building.name).all()
    groups = list(range(1, 5))
    stats = {}
    for g in groups:
        total = Inspection.query.filter_by(group_number=g).count()
        done = Inspection.query.filter_by(group_number=g, completed=True).count()
        stats[g] = {"total": total, "done": done}
    return render_template("summary.html", buildings=buildings, groups=groups, stats=stats)


@app.route("/api/summary/json")
def api_summary_json():
    inspections = Inspection.query.all()
    return jsonify([i.to_dict() for i in inspections])


# ── Init ──────────────────────────────────────────────────────────────────────

@app.cli.command("init-db")
def init_db():
    """Create tables and seed building data."""
    db.create_all()
    seed_buildings()
    print("DB initialized and buildings seeded.")


@app.before_request
def ensure_tables():
    pass


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_buildings()
    app.run(debug=True, host="0.0.0.0", port=5000)

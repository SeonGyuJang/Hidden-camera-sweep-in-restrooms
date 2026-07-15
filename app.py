import os
import base64
import json
import uuid
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

# ── Storage paths ─────────────────────────────────────────────────────────────
# On fly.io: DATA_DIR=/data (volume mount).  Locally: DATA_DIR=. (project root)
DATA_DIR    = os.environ.get("DATA_DIR", ".")
UPLOAD_DIR  = os.path.join(DATA_DIR, "photos")
os.makedirs(UPLOAD_DIR, exist_ok=True)

database_url = os.environ.get("DATABASE_URL",
                               f"sqlite:///{os.path.join(DATA_DIR, 'inspection.db')}")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

db = SQLAlchemy(app)
migrate = Migrate(app, db)


def save_photo(data_url: str) -> str:
    """Base64 data URL → 파일 저장 → 파일명 반환"""
    header, encoded = data_url.split(",", 1)
    mime = header.split(":")[1].split(";")[0]
    ext  = "jpg" if "jpeg" in mime else mime.split("/")[1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(base64.b64decode(encoded))
    return filename

# ── Static team config ────────────────────────────────────────────────────────

TEAMS = {
    "A": {
        "name": "도보A팀",
        "move_type": "도보",
        "color": "#3B82F6",
        "bg": "#EFF6FF",
        "members": ["오미령", "문재준"],
        "partners": [{"name": "디지털성범죄피해자지원센터", "icon": "🤝"}],
        "buildings": ["신정문 주차장", "학술정보원", "농심국제관"],
        "guide": "신정문에서 시작하여 학술정보원, 농심국제관 순으로 이동합니다.",
    },
    "B": {
        "name": "도보B팀",
        "move_type": "도보",
        "color": "#10B981",
        "bg": "#ECFDF5",
        "members": ["김종욱", "정승훈", "백서영"],
        "partners": [{"name": "세종북부경찰서", "icon": "🚔"}],
        "buildings": ["공공정책관", "과학기술2관", "호연학사(미래관 1층)"],
        "guide": "공공정책관에서 시작하여 과학기술2관, 호연학사 순으로 이동합니다.",
    },
    "C": {
        "name": "차량C팀",
        "move_type": "차량",
        "color": "#F59E0B",
        "bg": "#FFFBEB",
        "members": ["서홍욱", "민서현"],
        "partners": [{"name": "디지털성범죄피해자지원센터", "icon": "🤝"}],
        "buildings": ["산학협력관", "과학기술1관", "가속기ICT융합관"],
        "guide": "차량으로 이동하며 산학협력관, 과학기술1관, 가속기ICT융합관 순으로 점검합니다.",
    },
    "D": {
        "name": "차량D팀",
        "move_type": "차량",
        "color": "#8B5CF6",
        "bg": "#F5F3FF",
        "members": ["장선규", "김바다"],
        "partners": [{"name": "세종북부경찰서", "icon": "🚔"}],
        "buildings": ["학생회관", "석원경상관", "문화스포츠관"],
        "guide": "차량으로 이동하며 학생회관, 석원경상관, 문화스포츠관 순으로 점검합니다.",
    },
}

BUILDINGS_SEED = [
    {"name": "신정문 주차장",       "team": "A", "lat": 36.5972, "lng": 127.2855},
    {"name": "학술정보원",          "team": "A", "lat": 36.6002, "lng": 127.2878},
    {"name": "농심국제관",          "team": "A", "lat": 36.6018, "lng": 127.2898},
    {"name": "공공정책관",          "team": "B", "lat": 36.5995, "lng": 127.2862},
    {"name": "과학기술2관",         "team": "B", "lat": 36.5982, "lng": 127.2848},
    {"name": "호연학사(미래관 1층)","team": "B", "lat": 36.5965, "lng": 127.2872},
    {"name": "산학협력관",          "team": "C", "lat": 36.5990, "lng": 127.2905},
    {"name": "과학기술1관",         "team": "C", "lat": 36.5978, "lng": 127.2870},
    {"name": "가속기ICT융합관",     "team": "C", "lat": 36.5962, "lng": 127.2845},
    {"name": "학생회관",            "team": "D", "lat": 36.5988, "lng": 127.2892},
    {"name": "석원경상관",          "team": "D", "lat": 36.6008, "lng": 127.2908},
    {"name": "문화스포츠관",        "team": "D", "lat": 36.5952, "lng": 127.2888},
]

# Checklist items (ordered)
CHECKLIST = [
    ("partition",  "칸막이",    "칸막이 및 문 틈새 확인"),
    ("ceiling",    "천장",      "천장 및 환풍구 확인"),
    ("drain",      "배수구",    "배수구·바닥 틈새 확인"),
    ("outlet",     "콘센트",    "콘센트 및 전기 시설 확인"),
    ("trash",      "쓰레기통",  "쓰레기통 내·외부 확인"),
    ("fixture",    "기타 설치물","의심 설치물 전체 확인"),
]

# ── Models ────────────────────────────────────────────────────────────────────

class Building(db.Model):
    __tablename__ = "buildings"
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    team = db.Column(db.String(2),   nullable=False)
    lat  = db.Column(db.Float,       nullable=False)
    lng  = db.Column(db.Float,       nullable=False)
    restrooms = db.relationship("Restroom", backref="building", lazy=True,
                                cascade="all, delete-orphan")

    def to_dict(self):
        done = sum(1 for r in self.restrooms if any(i.completed for i in r.inspections))
        return {
            "id": self.id, "name": self.name, "team": self.team,
            "lat": self.lat, "lng": self.lng,
            "color": TEAMS[self.team]["color"],
            "total_restrooms": len(self.restrooms),
            "done_restrooms": done,
        }


class Restroom(db.Model):
    __tablename__ = "restrooms"
    id              = db.Column(db.Integer, primary_key=True)
    building_id     = db.Column(db.Integer, db.ForeignKey("buildings.id"), nullable=False)
    floor           = db.Column(db.String(20),  nullable=False)
    gender          = db.Column(db.String(10),  nullable=False)
    location_detail = db.Column(db.String(200))
    inspections = db.relationship("Inspection", backref="restroom", lazy=True,
                                  cascade="all, delete-orphan")

    @property
    def label(self):
        return f"{self.building.name} {self.floor} {self.gender}화장실"

    @property
    def status(self):
        if not self.inspections:
            return "pending"
        if any(i.completed for i in self.inspections):
            return "done"
        return "in_progress"

    def to_dict(self):
        return {
            "id": self.id,
            "building_id": self.building_id,
            "building_name": self.building.name,
            "floor": self.floor,
            "gender": self.gender,
            "location_detail": self.location_detail or "",
            "status": self.status,
            "team": self.building.team,
            "inspection_count": len(self.inspections),
        }


class Inspection(db.Model):
    __tablename__ = "inspections"
    id             = db.Column(db.Integer, primary_key=True)
    restroom_id    = db.Column(db.Integer, db.ForeignKey("restrooms.id"), nullable=False)
    team           = db.Column(db.String(2),   nullable=False)
    inspector_name = db.Column(db.String(100))
    before_photo   = db.Column(db.Text)
    after_photo    = db.Column(db.Text)
    photos         = db.Column(db.Text)   # JSON array of base64 data URLs
    photo_lat      = db.Column(db.Float)
    photo_lng      = db.Column(db.Float)
    # Checklist (boolean per item)
    chk_partition  = db.Column(db.Boolean, default=False)
    chk_ceiling    = db.Column(db.Boolean, default=False)
    chk_drain      = db.Column(db.Boolean, default=False)
    chk_outlet     = db.Column(db.Boolean, default=False)
    chk_trash      = db.Column(db.Boolean, default=False)
    chk_fixture    = db.Column(db.Boolean, default=False)
    # Result
    action_taken   = db.Column(db.Boolean, default=False)
    action_detail  = db.Column(db.Text)
    notes          = db.Column(db.Text)
    completed      = db.Column(db.Boolean, default=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def photos_list(self):
        if self.photos:
            try:
                return json.loads(self.photos)
            except Exception:
                return []
        return []

    @property
    def checklist_score(self):
        items = [self.chk_partition, self.chk_ceiling, self.chk_drain,
                 self.chk_outlet, self.chk_trash, self.chk_fixture]
        return sum(1 for x in items if x)

    def to_dict(self):
        return {
            "id": self.id,
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
            "checklist_score": self.checklist_score,
            "photo_count": len(self.photos_list),
            "photos": [f"/uploads/{f}" for f in self.photos_list],
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


# ── Context processor ─────────────────────────────────────────────────────────

app.jinja_env.filters['enumerate'] = enumerate

@app.context_processor
def inject_globals():
    return dict(TEAMS=TEAMS, CHECKLIST=CHECKLIST)


# ── Home ──────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    team_stats = {}
    total_done = 0
    total_all  = 0
    for tid in TEAMS:
        bids = [b.id for b in Building.query.filter_by(team=tid).all()]
        restrooms = Restroom.query.filter(Restroom.building_id.in_(bids)).all() if bids else []
        done = sum(1 for r in restrooms if r.status == "done")
        team_stats[tid] = {
            "total": len(restrooms),
            "done": done,
            "inspections": Inspection.query.filter_by(team=tid).count(),
            "actions": Inspection.query.filter_by(team=tid, action_taken=True).count(),
        }
        total_done += done
        total_all  += len(restrooms)
    overall_pct = int(total_done / total_all * 100) if total_all else 0
    recent = Inspection.query.order_by(Inspection.created_at.desc()).limit(5).all()
    return render_template("home.html", team_stats=team_stats,
                           total_done=total_done, total_all=total_all,
                           overall_pct=overall_pct, recent=recent)


# ── Team page ─────────────────────────────────────────────────────────────────

@app.route("/team/<tid>")
def team_page(tid):
    if tid not in TEAMS:
        return redirect(url_for("home"))
    buildings = Building.query.filter_by(team=tid).all()
    return render_template("team.html", tid=tid, buildings=buildings)


# ── Building page ─────────────────────────────────────────────────────────────

@app.route("/building/<int:bid>")
def building_page(bid):
    b = Building.query.get_or_404(bid)
    return render_template("building.html", b=b)


# ── Restroom add (from building page) ─────────────────────────────────────────

@app.route("/building/<int:bid>/add-restroom", methods=["GET", "POST"])
def restroom_add(bid):
    b = Building.query.get_or_404(bid)
    if request.method == "POST":
        r = Restroom(
            building_id=bid,
            floor=request.form["floor"],
            gender=request.form["gender"],
            location_detail=request.form.get("location_detail", ""),
        )
        db.session.add(r)
        db.session.commit()
        flash("화장실이 등록되었습니다.", "success")
        return redirect(url_for("building_page", bid=bid))
    return render_template("restroom_add.html", b=b)


@app.route("/restroom/<int:rid>/delete", methods=["POST"])
def restroom_delete(rid):
    r = Restroom.query.get_or_404(rid)
    bid = r.building_id
    db.session.delete(r)
    db.session.commit()
    flash("삭제되었습니다.", "info")
    return redirect(url_for("building_page", bid=bid))


# Keep legacy routes for drawer links
@app.route("/restrooms")
def restrooms():
    buildings = Building.query.order_by(Building.team, Building.name).all()
    return render_template("restrooms_overview.html", buildings=buildings)


@app.route("/restrooms/new", methods=["GET", "POST"])
def restroom_new():
    buildings = Building.query.order_by(Building.team, Building.name).all()
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
        return redirect(url_for("building_page", bid=r.building_id))
    prefill_bid = request.args.get("building_id", type=int)
    return render_template("restroom_new.html", buildings=buildings, prefill_bid=prefill_bid)


# ── Inspection ────────────────────────────────────────────────────────────────

@app.route("/inspect/<int:rid>", methods=["GET", "POST"])
def inspect(rid):
    """Dedicated inspection page for one restroom."""
    restroom = Restroom.query.get_or_404(rid)
    if request.method == "POST":
        lat = request.form.get("photo_lat") or None
        lng = request.form.get("photo_lng") or None
        insp = Inspection(
            restroom_id=rid,
            team=request.form.get("team", "A"),
            inspector_name=request.form.get("inspector_name", ""),
            before_photo=None,
            after_photo=None,
            photos=json.dumps([
                save_photo(p) for p in request.form.getlist("photos[]") if p
            ]) or None,
            photo_lat=float(lat) if lat else None,
            photo_lng=float(lng) if lng else None,
            chk_partition=bool(request.form.get("chk_partition")),
            chk_ceiling=bool(request.form.get("chk_ceiling")),
            chk_drain=bool(request.form.get("chk_drain")),
            chk_outlet=bool(request.form.get("chk_outlet")),
            chk_trash=bool(request.form.get("chk_trash")),
            chk_fixture=bool(request.form.get("chk_fixture")),
            action_taken=bool(request.form.get("action_taken")),
            action_detail=request.form.get("action_detail", ""),
            notes=request.form.get("notes", ""),
            completed=bool(request.form.get("completed")),
        )
        db.session.add(insp)
        db.session.commit()
        return redirect(url_for("inspect_done", iid=insp.id))
    # Get previous inspection to show existing data
    prev = Inspection.query.filter_by(restroom_id=rid).order_by(Inspection.created_at.desc()).first()
    return render_template("inspect.html", restroom=restroom, prev=prev)


@app.route("/inspect/done/<int:iid>")
def inspect_done(iid):
    insp = Inspection.query.get_or_404(iid)
    # Next restroom in same building
    restrooms = Restroom.query.filter_by(building_id=insp.restroom.building_id).order_by(Restroom.floor, Restroom.gender).all()
    ids = [r.id for r in restrooms]
    cur_idx = ids.index(insp.restroom_id) if insp.restroom_id in ids else -1
    next_rid = ids[cur_idx + 1] if cur_idx >= 0 and cur_idx + 1 < len(ids) else None
    return render_template("inspect_done.html", insp=insp, next_rid=next_rid)


# ── Records ───────────────────────────────────────────────────────────────────

@app.route("/records")
def records():
    team = request.args.get("team")
    q = Inspection.query.join(Restroom).join(Building)
    if team:
        q = q.filter(Inspection.team == team)
    items = q.order_by(Inspection.created_at.desc()).all()
    return render_template("records.html", items=items, sel_team=team)


@app.route("/records/<int:iid>")
def record_detail(iid):
    insp = Inspection.query.get_or_404(iid)
    return render_template("record_detail.html", insp=insp)


@app.route("/records/<int:iid>/edit", methods=["GET", "POST"])
def record_edit(iid):
    insp = Inspection.query.get_or_404(iid)
    if request.method == "POST":
        insp.team = request.form.get("team", insp.team)
        insp.inspector_name = request.form.get("inspector_name", "")
        new_raw = [p for p in request.form.getlist("photos[]") if p]
        # Separate already-saved filenames from new base64 uploads
        saved, uploads = [], []
        for p in new_raw:
            (uploads if p.startswith("data:") else saved).append(p)
        new_files = [save_photo(p) for p in uploads]
        insp.photos = json.dumps(saved + new_files) or None
        insp.chk_partition = bool(request.form.get("chk_partition"))
        insp.chk_ceiling   = bool(request.form.get("chk_ceiling"))
        insp.chk_drain     = bool(request.form.get("chk_drain"))
        insp.chk_outlet    = bool(request.form.get("chk_outlet"))
        insp.chk_trash     = bool(request.form.get("chk_trash"))
        insp.chk_fixture   = bool(request.form.get("chk_fixture"))
        insp.action_taken  = bool(request.form.get("action_taken"))
        insp.action_detail = request.form.get("action_detail", "")
        insp.notes         = request.form.get("notes", "")
        insp.completed     = bool(request.form.get("completed"))
        insp.updated_at    = datetime.utcnow()
        db.session.commit()
        flash("수정되었습니다.", "success")
        return redirect(url_for("record_detail", iid=insp.id))
    return render_template("record_edit.html", insp=insp)


@app.route("/records/<int:iid>/delete", methods=["POST"])
def record_delete(iid):
    insp = Inspection.query.get_or_404(iid)
    db.session.delete(insp)
    db.session.commit()
    return redirect(url_for("records"))


@app.route("/uploads/<path:filename>")
def serve_photo(filename):
    """Volume에 저장된 사진 파일 서빙"""
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(path):
        return "없음", 404
    return send_file(path)


@app.route("/records/<int:iid>/photo/<which>")
def record_photo(iid, which):
    """개별 사진 다운로드"""
    insp = Inspection.query.get_or_404(iid)
    try:
        idx = int(which)
        photos = json.loads(insp.photos) if insp.photos else []
        filename = photos[idx] if 0 <= idx < len(photos) else None
    except (ValueError, IndexError):
        filename = None
    if not filename:
        return "없음", 404
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(path):
        return "없음", 404
    return send_file(path, as_attachment=True,
                     download_name=f"insp_{iid}_{which}.jpg")


# ── Summary ───────────────────────────────────────────────────────────────────

@app.route("/summary")
def summary():
    team_stats = {}
    for tid in TEAMS:
        bids = [b.id for b in Building.query.filter_by(team=tid).all()]
        restrooms = Restroom.query.filter(Restroom.building_id.in_(bids)).all() if bids else []
        done = sum(1 for r in restrooms if r.status == "done")
        actions = Inspection.query.filter_by(team=tid, action_taken=True).all()
        team_stats[tid] = {
            "total": len(restrooms),
            "done": done,
            "pct": int(done / len(restrooms) * 100) if restrooms else 0,
            "inspections": Inspection.query.filter_by(team=tid).count(),
            "actions": len(actions),
            "action_list": actions,
        }
    buildings = Building.query.order_by(Building.team, Building.name).all()
    return render_template("summary.html", team_stats=team_stats, buildings=buildings)


@app.route("/api/export")
def api_export():
    return jsonify([i.to_dict() for i in Inspection.query.all()])


# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    result = {}
    for b in Building.query.all():
        result[b.id] = {
            "building": b.name,
            "restrooms": [r.to_dict() for r in b.restrooms]
        }
    return jsonify(result)


# ── CLI ───────────────────────────────────────────────────────────────────────

@app.cli.command("init-db")
def init_db():
    db.create_all()
    seed_buildings()
    print("Done.")


if __name__ == "__main__":
    with app.app_context():
        try:
            Building.query.count()
        except Exception:
            print("[init] 스키마 변경 → DB 재생성")
            db.drop_all()
        db.create_all()
        seed_buildings()
    app.run(debug=True, host="0.0.0.0", port=5000)

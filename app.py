import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, abort, g, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from config import Config
from models import Base, Thread, Project, Actor, Event, Surface, Episode, utcnow
from domain.queries import (
    get_living_threads,
    get_cockpit_queues,
    get_all_projects,
    get_thread_by_id,
    get_current_focus_thread,
    VALID_DOMAINS,
    ATTENTION_MODES
)
from domain.transitions import (
    set_current_focus,
    park_thread,
    resume_thread,
    make_decision,
    append_event
)
from seed import seed_database

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    db_session = scoped_session(sessionmaker(bind=engine))

    @app.before_request
    def before_request():
        g.db = db_session()

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    @app.context_processor
    def inject_global_state():
        focus_thread = get_current_focus_thread(g.db) if hasattr(g, 'db') else None
        return {
            "current_focus_thread": focus_thread,
            "all_attention_modes": ATTENTION_MODES,
            "all_domains": VALID_DOMAINS,
        }

    # CLI Command to seed database
    @app.cli.command("seed-db")
    def cli_seed_db():
        seed_database(engine)
        print("Database seeded successfully via CLI.")

    # Ensure tables exist on boot
    Base.metadata.create_all(engine)

    # -------------------------------------------------------------
    # Primary Routes
    # -------------------------------------------------------------

    @app.route("/")
    def cockpit():
        domain = request.args.get("domain", "All")
        mode = request.args.get("mode", "ALL")
        project_id = request.args.get("project_id", type=int)
        search_query = request.args.get("q", "").strip()

        threads = get_living_threads(
            g.db,
            domain=domain,
            project_id=project_id,
            attention_mode=mode,
            search_query=search_query
        )
        queues = get_cockpit_queues(threads)
        projects = get_all_projects(g.db)
        total_living = sum(len(q) for q in queues.values())

        return render_template(
            "cockpit.html",
            active_view="now",
            queues=queues,
            projects=projects,
            domains=VALID_DOMAINS,
            modes=ATTENTION_MODES,
            current_domain=domain,
            current_mode=mode.upper(),
            current_project_id=project_id,
            total_living=total_living
        )

    @app.route("/queues")
    def cockpit_queues_partial():
        domain = request.args.get("domain", "All")
        mode = request.args.get("mode", "ALL")
        project_id = request.args.get("project_id", type=int)
        search_query = request.args.get("q", "").strip()

        threads = get_living_threads(
            g.db,
            domain=domain,
            project_id=project_id,
            attention_mode=mode,
            search_query=search_query
        )
        queues = get_cockpit_queues(threads)

        return render_template("_queues.html", queues=queues)

    @app.route("/threads/<int:thread_id>/drawer")
    def thread_drawer(thread_id: int):
        thread = get_thread_by_id(g.db, thread_id)
        if not thread:
            abort(404)
        return render_template("_thread_drawer.html", thread=thread)

    @app.route("/threads/<int:thread_id>")
    def thread_workspace_view(thread_id: int):
        """Dedicated full Thread Workspace with Activity Braid & Working Set."""
        thread = get_thread_by_id(g.db, thread_id)
        if not thread:
            abort(404)
        return render_template(
            "thread_workspace.html",
            thread=thread,
            active_view="workspace",
            current_domain=thread.domain,
            current_mode=thread.attention_fit or "FOCUS"
        )

    @app.route("/living")
    def mission_control():
        domain = request.args.get("domain", "All")
        search_query = request.args.get("q", "").strip()

        threads = get_living_threads(
            g.db,
            domain=domain,
            search_query=search_query,
            include_parked=True
        )

        return render_template(
            "mission_control.html",
            active_view="mission_control",
            threads=threads,
            domains=VALID_DOMAINS,
            current_domain=domain,
            current_mode="ALL"
        )

    # -------------------------------------------------------------
    # Multi-Channel Parallel Cockpit Routes (Burst 3)
    # -------------------------------------------------------------

    @app.route("/parallel")
    def parallel_cockpit():
        cols = request.args.get("cols", default=3, type=int)
        cols = max(2, min(4, cols))

        all_threads = get_living_threads(g.db, include_parked=True)
        freq_presets = ["140.85", "140.96", "141.12", "141.80"]
        channel_thread_ids = []
        channels = []

        for i in range(cols):
            param_key = f"ch{i+1}"
            default_id = all_threads[i].id if i < len(all_threads) else (all_threads[0].id if all_threads else 1)
            t_id = request.args.get(param_key, default=default_id, type=int)
            channel_thread_ids.append(t_id)

            t = get_thread_by_id(g.db, t_id) or (all_threads[0] if all_threads else None)
            channels.append({
                "thread": t,
                "freq": freq_presets[i % len(freq_presets)],
                "channel_num": i + 1
            })

        return render_template(
            "parallel_cockpit.html",
            active_view="parallel",
            col_count=cols,
            channels=channels,
            channel_thread_ids=channel_thread_ids,
            all_living_threads=all_threads,
            current_domain="All",
            current_mode="ALL"
        )

    @app.route("/channels/<int:channel_num>/thread/<int:thread_id>")
    def channel_thread_view(channel_num: int, thread_id: int):
        thread = get_thread_by_id(g.db, thread_id)
        if not thread:
            abort(404)
        all_threads = get_living_threads(g.db, include_parked=True)
        freq_presets = ["140.85", "140.96", "141.12", "141.80"]
        freq = freq_presets[(channel_num - 1) % len(freq_presets)]
        return render_template(
            "_channel_pane.html",
            channel_num=channel_num,
            freq=freq,
            thread=thread,
            all_living_threads=all_threads
        )

    @app.route("/channels/<int:channel_num>/thread/<int:thread_id>/decide", methods=["POST"])
    def channel_thread_decide(channel_num: int, thread_id: int):
        choice = request.form.get("choice")
        reasoning = request.form.get("reasoning")
        make_decision(g.db, thread_id, choice=choice, reasoning=reasoning)
        return redirect(url_for("channel_thread_view", channel_num=channel_num, thread_id=thread_id))

    @app.route("/channels/<int:channel_num>/thread/<int:thread_id>/events", methods=["POST"])
    def channel_thread_events(channel_num: int, thread_id: int):
        summary = request.form.get("summary", "").strip()
        event_type = request.form.get("event_type", "NOTE").upper()
        if summary:
            append_event(g.db, thread_id, event_type=event_type, summary=summary)
        return redirect(url_for("channel_thread_view", channel_num=channel_num, thread_id=thread_id))

    @app.route("/channels/<int:channel_num>/thread/<int:thread_id>/park", methods=["POST"])
    def channel_thread_park(channel_num: int, thread_id: int):
        note = request.form.get("note")
        resume_condition = request.form.get("resume_condition")
        park_thread(g.db, thread_id, note=note, resume_condition=resume_condition)
        return redirect(url_for("channel_thread_view", channel_num=channel_num, thread_id=thread_id))

    @app.route("/channels/<int:channel_num>/thread/<int:thread_id>/resume", methods=["POST"])
    def channel_thread_resume(channel_num: int, thread_id: int):
        resume_thread(g.db, thread_id)
        return redirect(url_for("channel_thread_view", channel_num=channel_num, thread_id=thread_id))

    @app.route("/channels/<int:channel_num>/thread/<int:thread_id>/focus", methods=["POST"])
    def channel_thread_focus(channel_num: int, thread_id: int):
        set_current_focus(g.db, thread_id)
        return redirect(url_for("channel_thread_view", channel_num=channel_num, thread_id=thread_id))


    # -------------------------------------------------------------
    # State Transition Action Endpoints
    # -------------------------------------------------------------

    @app.route("/threads/<int:thread_id>/focus", methods=["POST"])
    def thread_set_focus(thread_id: int):
        set_current_focus(g.db, thread_id)
        return redirect(url_for("thread_workspace_view", thread_id=thread_id))

    @app.route("/threads/<int:thread_id>/park", methods=["POST"])
    def thread_park_action(thread_id: int):
        note = request.form.get("note")
        resume_condition = request.form.get("resume_condition")
        park_thread(g.db, thread_id, note=note, resume_condition=resume_condition)
        return redirect(url_for("cockpit"))

    @app.route("/threads/<int:thread_id>/resume", methods=["POST"])
    def thread_resume_action(thread_id: int):
        resume_thread(g.db, thread_id)
        return redirect(url_for("thread_workspace_view", thread_id=thread_id))

    @app.route("/threads/<int:thread_id>/decide", methods=["POST"])
    def thread_decide(thread_id: int):
        choice = request.form.get("choice")
        reasoning = request.form.get("reasoning")
        make_decision(g.db, thread_id, choice=choice, reasoning=reasoning)
        return redirect(url_for("thread_workspace_view", thread_id=thread_id))

    @app.route("/threads/<int:thread_id>/events", methods=["POST"])
    def thread_add_event(thread_id: int):
        summary = request.form.get("summary", "").strip()
        event_type = request.form.get("event_type", "NOTE").upper()
        if summary:
            append_event(g.db, thread_id, event_type=event_type, summary=summary)
        return redirect(url_for("thread_workspace_view", thread_id=thread_id))

    @app.route("/threads", methods=["POST"])
    def create_thread():
        name = request.form.get("name", "").strip()
        intent = request.form.get("intent", "").strip()
        if not name:
            return redirect(url_for("cockpit"))

        thread = Thread(
            name=name,
            intent=intent or None,
            frontier="Initial thread created. Frontier needs articulation.",
            state="READY",
            attention_fit="FOCUS",
            is_living=True,
            is_current_focus=True,
            created_at=utcnow(),
            last_active_at=utcnow()
        )
        g.db.add(thread)
        g.db.commit()

        # Append creation event
        append_event(g.db, thread.id, event_type="THREAD_CREATED", summary=f"Thread '{name}' created.")
        return redirect(url_for("thread_workspace_view", thread_id=thread.id))

    # -------------------------------------------------------------
    # REST APIs
    # -------------------------------------------------------------

    @app.route("/api/threads", methods=["GET"])
    def api_threads():
        domain = request.args.get("domain")
        threads = get_living_threads(g.db, domain=domain, include_parked=True)
        return jsonify([t.to_dict() for t in threads])

    @app.route("/api/threads/<int:thread_id>", methods=["GET"])
    def api_thread_detail(thread_id: int):
        thread = get_thread_by_id(g.db, thread_id)
        if not thread:
            return jsonify({"error": "Thread not found"}), 404
        return jsonify(thread.compile_briefing())

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"\n=======================================================")
    print(f"  CODEC // TACTICAL CONTROL PLANE (FREQ 140.85)")
    print(f"  Live Cockpit: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host="127.0.0.1", port=port, debug=True)

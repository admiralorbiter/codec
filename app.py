import os
import json
import time
import queue
from pathlib import Path
from flask import Flask, render_template, request, jsonify, abort, g, redirect, url_for, Response, stream_with_context
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from config import Config
from models import Base, Thread, Project, Actor, Event, Surface, Episode, WorkPacket, utcnow
from domain.sse_service import broadcaster
from domain.queries import (
    get_living_threads,
    get_cockpit_queues,
    get_all_projects,
    get_thread_by_id,
    get_current_focus_thread,
    VALID_DOMAINS,
    ATTENTION_MODES,
    compile_ai_context_packet,
    generate_smart_commit_message,
    get_thread_relations
)
from domain.transitions import (
    set_current_focus,
    park_thread,
    resume_thread,
    make_decision,
    append_event,
    close_thread,
    update_thread_frontier,
    accept_result,
    rework_result,
    add_surface,
    delete_surface,
    parse_capture_transcript,
    commit_capture,
    log_friction,
    add_thread_relation,
    delete_thread_relation,
    create_decision_gate,
    create_work_packet,
    dispatch_work_packet,
    deliver_work_packet_result,
    adopt_work_packet_result,
    request_work_packet_rework
)
from domain.git_service import (
    sync_thread_git_working_set,
    inspect_git_working_set,
    git_commit_working_set
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
        relations = get_thread_relations(g.db, thread_id)
        all_living_threads = get_living_threads(g.db, include_parked=True)
        return render_template(
            "thread_workspace.html",
            thread=thread,
            relations=relations,
            all_living_threads=all_living_threads,
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
            default_id = all_threads[i].id if i < len(all_threads) else (all_threads[0].id if all_threads else None)
            t_id = request.args.get(param_key, default=default_id, type=int)
            channel_thread_ids.append(t_id)

            t = get_thread_by_id(g.db, t_id) if t_id else (all_threads[0] if all_threads else None)
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

        # Reset any existing current focus
        g.db.query(Thread).filter(Thread.is_current_focus == True).update({"is_current_focus": False})

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


    @app.route("/threads/<int:thread_id>/close", methods=["POST"])
    def thread_close_action(thread_id: int):
        note = request.form.get("note")
        close_thread(g.db, thread_id, note=note)
        if request.headers.get("HX-Request"):
            return redirect(url_for("cockpit"))
        return redirect(url_for("cockpit"))

    @app.route("/threads/<int:thread_id>/update", methods=["POST"])
    def thread_update_action(thread_id: int):
        frontier = request.form.get("frontier")
        next_action = request.form.get("next_action")
        state = request.form.get("state")
        attention_fit = request.form.get("attention_fit")
        thread = update_thread_frontier(
            g.db, thread_id,
            frontier=frontier,
            next_action=next_action,
            state=state,
            attention_fit=attention_fit
        )
        if request.headers.get("HX-Request"):
            return render_template("_thread_drawer.html", thread=thread)
        return redirect(url_for("thread_workspace_view", thread_id=thread_id))

    @app.route("/threads/<int:thread_id>/accept", methods=["POST"])
    def thread_accept_action(thread_id: int):
        note = request.form.get("note")
        updated_frontier = request.form.get("frontier")
        thread = accept_result(g.db, thread_id, note=note, updated_frontier=updated_frontier)
        if request.headers.get("HX-Request"):
            return render_template("_thread_drawer.html", thread=thread)
        return redirect(url_for("thread_workspace_view", thread_id=thread_id))

    @app.route("/threads/<int:thread_id>/rework", methods=["POST"])
    def thread_rework_action(thread_id: int):
        feedback = request.form.get("feedback", "Rework requested.")
        thread = rework_result(g.db, thread_id, feedback=feedback)
        if request.headers.get("HX-Request"):
            return render_template("_thread_drawer.html", thread=thread)
        return redirect(url_for("thread_workspace_view", thread_id=thread_id))

    @app.route("/threads/<int:thread_id>/surfaces", methods=["POST"])
    def thread_add_surface(thread_id: int):
        surface_type = request.form.get("surface_type", "OTHER")
        label = request.form.get("label", "").strip()
        uri = request.form.get("uri", "").strip()
        local_path = request.form.get("local_path", "").strip()
        provider = request.form.get("provider", "").strip()
        if label:
            add_surface(g.db, thread_id, surface_type=surface_type, label=label, uri=uri, local_path=local_path, provider=provider)
        thread = get_thread_by_id(g.db, thread_id)
        if request.headers.get("HX-Request"):
            return render_template("_thread_drawer.html", thread=thread)
        return redirect(url_for("thread_workspace_view", thread_id=thread_id))

    @app.route("/surfaces/<int:surface_id>/delete", methods=["POST"])
    def surface_delete(surface_id: int):
        thread_id = request.form.get("thread_id", type=int)
        delete_surface(g.db, surface_id)
        if thread_id:
            return redirect(url_for("thread_workspace_view", thread_id=thread_id))
        return redirect(url_for("cockpit"))

    # -------------------------------------------------------------
    # Horizon 1: Git Sync, Context Packets & Cross-Thread Relations
    # -------------------------------------------------------------

    @app.route("/threads/<int:thread_id>/git-sync", methods=["POST"])
    def thread_git_sync(thread_id: int):
        working_set = sync_thread_git_working_set(g.db, thread_id, append_diff_event=True)
        thread = get_thread_by_id(g.db, thread_id)
        if request.headers.get("HX-Request"):
            return render_template("_working_set.html", thread=thread)
        return redirect(url_for("thread_workspace_view", thread_id=thread_id))

    @app.route("/threads/<int:thread_id>/git-commit", methods=["POST"])
    def thread_git_commit(thread_id: int):
        commit_message = request.form.get("commit_message", "").strip()
        do_push = request.form.get("do_push") in ["true", "on", "1"]

        if not commit_message:
            commit_message = "feat: checkpoint update from Codec control plane"

        thread = get_thread_by_id(g.db, thread_id)
        if not thread:
            abort(404)

        ws = thread.get_working_set()
        repo_path = ws.get("repo_path") or "."
        for s in thread.surfaces:
            if s.local_path and os.path.exists(s.local_path):
                repo_path = s.local_path
                break

        res = git_commit_working_set(repo_path, commit_message, do_push=do_push)

        if res.get("status") == "success":
            new_commit = res.get("commit")
            ev_summary = f"🌿 Git commit created: @{new_commit} — {commit_message}"
            if res.get("pushed"):
                ev_summary += " (pushed to remote)"
            event = Event(
                thread_id=thread.id,
                event_type="GIT_COMMIT",
                summary=ev_summary,
                payload_json=json.dumps(res),
                occurred_at=utcnow()
            )
            g.db.add(event)

            # Auto-advance thread frontier & next action
            thread.frontier = f"Checkpointed @{new_commit}: {commit_message}. Working tree clean."
            thread.next_action = f"Proceed from checkpoint @{new_commit} or review next architectural milestone."

            # Sync working set to refresh chips to clean state
            sync_thread_git_working_set(g.db, thread.id)
            g.db.commit()

        return redirect(url_for("thread_workspace_view", thread_id=thread.id))

    @app.route("/threads/<int:thread_id>/generate-commit-message", methods=["GET"])
    def thread_generate_commit_message(thread_id: int):
        thread = get_thread_by_id(g.db, thread_id)
        if not thread:
            return jsonify({"error": "Thread not found"}), 404
        msg = generate_smart_commit_message(thread)
        return jsonify({
            "status": "ok",
            "thread_id": thread_id,
            "commit_message": msg
        })



    @app.route("/threads/<int:thread_id>/context-packet", methods=["GET"])
    def thread_context_packet(thread_id: int):
        thread = get_thread_by_id(g.db, thread_id)
        if not thread:
            return jsonify({"error": "Thread not found"}), 404
        packet_md = compile_ai_context_packet(thread)
        return jsonify({
            "status": "ok",
            "thread_id": thread_id,
            "thread_name": thread.name,
            "packet": packet_md
        })

    @app.route("/threads/<int:thread_id>/decision-gate", methods=["POST"])
    def thread_create_decision_gate(thread_id: int):
        title = request.form.get("title", "").strip()
        opt1_title = request.form.get("opt1_title", "").strip()
        opt1_desc = request.form.get("opt1_desc", "").strip()
        opt2_title = request.form.get("opt2_title", "").strip()
        opt2_desc = request.form.get("opt2_desc", "").strip()
        opt3_title = request.form.get("opt3_title", "").strip()
        opt3_desc = request.form.get("opt3_desc", "").strip()
        recommended = request.form.get("recommended", "1")
        attention = request.form.get("attention", "2–5 min")

        options = []
        if opt1_title:
            options.append({"id": "opt1", "title": opt1_title, "desc": opt1_desc, "recommended": recommended == "1"})
        if opt2_title:
            options.append({"id": "opt2", "title": opt2_title, "desc": opt2_desc, "recommended": recommended == "2"})
        if opt3_title:
            options.append({"id": "opt3", "title": opt3_title, "desc": opt3_desc, "recommended": recommended == "3"})

        if title and options:
            create_decision_gate(g.db, thread_id, decision_title=title, options=options, estimated_attention=attention)

        return redirect(url_for("thread_workspace_view", thread_id=thread_id))

    @app.route("/threads/<int:thread_id>/relations", methods=["POST"])
    def thread_add_relation(thread_id: int):
        target_id = request.form.get("target_id", type=int)
        relation_type = request.form.get("relation_type", "DEPENDS_ON")
        note = request.form.get("note", "").strip()
        if target_id and target_id != thread_id:
            add_thread_relation(g.db, source_id=thread_id, target_id=target_id, relation_type=relation_type, note=note)
        return redirect(url_for("thread_workspace_view", thread_id=thread_id))

    @app.route("/relations/<int:relation_id>/delete", methods=["POST"])
    def relation_delete(relation_id: int):
        thread_id = request.form.get("thread_id", type=int)
        delete_thread_relation(g.db, relation_id)
        if thread_id:
            return redirect(url_for("thread_workspace_view", thread_id=thread_id))
        return redirect(url_for("cockpit"))


    # -------------------------------------------------------------
    # Universal Capture & Friction Logging Endpoints
    # -------------------------------------------------------------

    @app.route("/capture/preview", methods=["POST"])
    def capture_preview():
        data = request.get_json() if request.is_json else request.form
        transcript = data.get("transcript", "")
        proposal = parse_capture_transcript(g.db, transcript)
        return jsonify(proposal)

    @app.route("/capture/commit", methods=["POST"])
    def capture_commit():
        data = request.get_json() if request.is_json else request.form.to_dict()
        thread = commit_capture(g.db, data)
        if request.is_json:
            return jsonify({"status": "ok", "thread_id": thread.id, "redirect_url": url_for("thread_workspace_view", thread_id=thread.id)})
        return redirect(url_for("thread_workspace_view", thread_id=thread.id))

    @app.route("/friction", methods=["POST"])
    def record_friction():
        note = request.form.get("note", "").strip()
        category = request.form.get("category", "FRICTION")
        page_url = request.form.get("page_url")
        thread_id = request.form.get("thread_id", type=int)
        if note:
            log_friction(g.db, note=note, category=category, page_url=page_url, thread_id=thread_id)
        return jsonify({"status": "recorded", "message": "Friction logged. Thank you for the telemetry."})


    # -------------------------------------------------------------
    # Horizon 2: Work Packet & Dispatch Engine Routes
    # -------------------------------------------------------------

    @app.route("/threads/<int:thread_id>/work-packets", methods=["POST"])
    def thread_create_work_packet(thread_id: int):
        desired_outcome = request.form.get("desired_outcome", "").strip()
        constraints = request.form.get("constraints", "").strip() or None
        stop_conditions = request.form.get("stop_conditions", "").strip() or None
        authority_level = request.form.get("authority_level", "EXECUTE_AND_TEST")
        expected_evidence = request.form.get("expected_evidence", "").strip() or "Passing test suite & git working set diff"
        review_requirement = request.form.get("review_requirement", "MANDATORY_HUMAN_REVIEW")

        if not desired_outcome:
            abort(400, description="Desired outcome is required")

        packet = create_work_packet(
            g.db,
            thread_id=thread_id,
            desired_outcome=desired_outcome,
            constraints=constraints,
            stop_conditions=stop_conditions,
            authority_level=authority_level,
            expected_evidence=expected_evidence,
            review_requirement=review_requirement
        )

        auto_dispatch = request.form.get("auto_dispatch") in ["true", "on", "1"]
        if auto_dispatch:
            dispatch_work_packet(g.db, packet.id, actor_name=request.form.get("actor_name", "Antigravity"))

        return redirect(url_for("thread_workspace_view", thread_id=thread_id))

    @app.route("/work-packets/<int:packet_id>/dispatch", methods=["POST"])
    def work_packet_dispatch(packet_id: int):
        actor_name = request.form.get("actor_name", "Antigravity")
        packet = dispatch_work_packet(g.db, packet_id, actor_name=actor_name)
        return redirect(url_for("thread_workspace_view", thread_id=packet.thread_id))

    @app.route("/work-packets/<int:packet_id>/deliver", methods=["POST"])
    def work_packet_deliver(packet_id: int):
        data = request.get_json() if request.is_json else request.form.to_dict()
        result_summary = data.get("result_summary", "").strip() or "Delivered work packet implementation."
        evidence = data.get("evidence", "").strip() or None

        packet = deliver_work_packet_result(g.db, packet_id, result_summary=result_summary, evidence=evidence)
        if request.is_json:
            return jsonify({"status": "delivered", "work_packet": packet.to_dict()})
        return redirect(url_for("thread_workspace_view", thread_id=packet.thread_id))

    @app.route("/work-packets/<int:packet_id>/adopt", methods=["POST"])
    def work_packet_adopt(packet_id: int):
        packet = adopt_work_packet_result(g.db, packet_id)
        return redirect(url_for("thread_workspace_view", thread_id=packet.thread_id))

    @app.route("/work-packets/<int:packet_id>/rework", methods=["POST"])
    def work_packet_rework(packet_id: int):
        rework_feedback = request.form.get("rework_feedback", "").strip() or "Please revise implementation and address test issues."
        packet = request_work_packet_rework(g.db, packet_id, rework_feedback=rework_feedback)
        return redirect(url_for("thread_workspace_view", thread_id=packet.thread_id))

    @app.route("/threads/<int:thread_id>/work-packet/active", methods=["GET"])
    def thread_active_work_packet_api(thread_id: int):
        thread = get_thread_by_id(g.db, thread_id)
        if not thread:
            return jsonify({"error": "Thread not found"}), 404
        wp = getattr(thread, "active_work_packet", None)
        if not wp:
            return jsonify({"status": "none", "message": "No active work packet on thread."})
        return jsonify({"status": "active", "work_packet": wp.to_dict()})


    # -------------------------------------------------------------
    # Horizon 3: Live Real-Time Telemetry & SSE Streaming Routes
    # -------------------------------------------------------------

    @app.route("/api/stream", methods=["GET"])
    def api_global_stream():
        """Global SSE stream for cockpit and radar real-time updates."""
        def event_stream():
            q = broadcaster.subscribe()
            try:
                yield f"event: CONNECTED\ndata: {json.dumps({'status': 'connected', 'time': time.time()})}\n\n"
                while True:
                    try:
                        msg = q.get(timeout=25.0)
                        yield msg
                    except queue.Empty:
                        yield ": keepalive\n\n"
            finally:
                broadcaster.unsubscribe(q)

        return Response(stream_with_context(event_stream()), mimetype="text/event-stream")

    @app.route("/threads/<int:thread_id>/stream", methods=["GET"])
    def thread_event_stream(thread_id: int):
        """Thread-specific SSE stream for activity braid, frontier, and agent telemetry."""
        def event_stream():
            q = broadcaster.subscribe(thread_id=thread_id)
            try:
                yield f"event: CONNECTED\ndata: {json.dumps({'status': 'connected', 'thread_id': thread_id})}\n\n"
                while True:
                    try:
                        msg = q.get(timeout=25.0)
                        yield msg
                    except queue.Empty:
                        yield ": keepalive\n\n"
            finally:
                broadcaster.unsubscribe(q, thread_id=thread_id)

        return Response(stream_with_context(event_stream()), mimetype="text/event-stream")

    @app.route("/api/agent/telemetry", methods=["POST"])
    def agent_telemetry_post():
        """Ingests live agent execution step telemetry and broadcasts over SSE."""
        data = request.get_json() if request.is_json else request.form.to_dict()
        thread_id = data.get("thread_id")
        if thread_id is not None:
            try:
                thread_id = int(thread_id)
            except (ValueError, TypeError):
                thread_id = None

        step_name = data.get("step_name", "Executing task step")
        step_index = data.get("step_index", 1)
        total_steps = data.get("total_steps", 1)
        log_snippet = data.get("log_snippet", "")
        actor_name = data.get("actor_name", "Antigravity")

        telemetry_payload = {
            "thread_id": thread_id,
            "step_name": step_name,
            "step_index": step_index,
            "total_steps": total_steps,
            "log_snippet": log_snippet,
            "actor_name": actor_name
        }

        broadcaster.broadcast("AGENT_TELEMETRY", telemetry_payload, thread_id=thread_id)
        return jsonify({"status": "broadcasted", "telemetry": telemetry_payload})


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

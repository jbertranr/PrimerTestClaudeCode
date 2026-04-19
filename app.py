"""
Swiss Job Finder — Streamlit Dashboard
Run with:  streamlit run app.py
"""

import json
import os
import subprocess
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import yaml

from storage.status_db import init_status_db, get_all_statuses, set_status

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Swiss Job Finder — Arnaud",
    page_icon="🇨🇭",
    layout="wide",
)

JOBS_FILE = os.path.join("data", "jobs.json")
CONFIG_FILE = "config.yaml"

CATEGORY_LABELS = {
    "hospitality": "🍽️ Hôtellerie / Restauration",
    "tourism": "🗺️ Tourisme",
    "international": "🌐 Organisations Internationales",
}

STATUS_LABELS = {
    "new": "🆕 Nou",
    "interested": "⭐ Interessant",
    "applied": "✅ Aplicat",
    "discarded": "❌ Descartat",
}


# ── Data loading ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_jobs() -> list:
    if not os.path.exists(JOBS_FILE):
        return []
    with open(JOBS_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ── Init ──────────────────────────────────────────────────────────────────────
init_status_db()
all_jobs = load_jobs()
statuses = get_all_statuses()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🇨🇭 Swiss Job Finder — Arnaud")
if all_jobs:
    st.caption(f"{len(all_jobs)} ofertes guardades · última actualització: {all_jobs[0]['first_seen_at'][:10]}")
else:
    st.warning("Encara no hi ha dades. Fes **git pull** o llança una cerca des de la pestanya ⚙️ Configuració.")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📋 Avui", "🗂️ Historial", "📨 Candidatures", "⚙️ Configuració"])


# ════════════════════════════════════════════════════════════════
# TAB 1 — AVUI
# ════════════════════════════════════════════════════════════════
with tab1:
    today = datetime.utcnow().date().isoformat()
    today_jobs = [j for j in all_jobs if j.get("first_seen_at", "").startswith(today)]

    if not today_jobs:
        st.info("Encara no hi ha ofertes d'avui. GitHub Actions les afegirà a les 8:00.")
    else:
        hospitality = [j for j in today_jobs if j["category"] == "hospitality"]
        tourism = [j for j in today_jobs if j["category"] == "tourism"]
        international = [j for j in today_jobs if j["category"] == "international"]

        col1, col2, col3 = st.columns(3)
        col1.metric("🍽️ Hostaleria", len(hospitality))
        col2.metric("🗺️ Turisme", len(tourism))
        col3.metric("🌐 Internacional", len(international))
        st.divider()

        for category, jobs in [
            ("hospitality", hospitality),
            ("tourism", tourism),
            ("international", international),
        ]:
            if not jobs:
                continue
            st.subheader(CATEGORY_LABELS[category])
            for job in jobs:
                job_id = job["id"]
                current_status = statuses.get(job_id, "new")
                status_label = STATUS_LABELS.get(current_status, current_status)

                col_title, col_int, col_app, col_dis = st.columns([5, 1, 1, 1])
                with col_title:
                    st.markdown(
                        f"**[{job['title']}]({job['url']})** · {job['company']} · 📍{job['location']} · _{status_label}_"
                    )
                with col_int:
                    if st.button("⭐", key=f"int_{job_id}", help="Marcar com interessant"):
                        set_status(job_id, "interested")
                        st.rerun()
                with col_app:
                    if st.button("✅", key=f"app_{job_id}", help="He aplicat"):
                        set_status(job_id, "applied")
                        st.rerun()
                with col_dis:
                    if st.button("❌", key=f"dis_{job_id}", help="Descartar"):
                        set_status(job_id, "discarded")
                        st.rerun()


# ════════════════════════════════════════════════════════════════
# TAB 2 — HISTORIAL
# ════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Historial d'ofertes")

    col_days, col_cat, col_stat = st.columns(3)
    with col_days:
        days = st.selectbox("Període", [7, 14, 30], index=1, format_func=lambda d: f"Últims {d} dies")
    with col_cat:
        cat_filter = st.multiselect(
            "Categoria",
            options=list(CATEGORY_LABELS.keys()),
            format_func=lambda c: CATEGORY_LABELS[c],
        )
    with col_stat:
        stat_filter = st.multiselect(
            "Estat",
            options=list(STATUS_LABELS.keys()),
            format_func=lambda s: STATUS_LABELS[s],
        )

    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    filtered = [j for j in all_jobs if j.get("first_seen_at", "") >= since]
    if cat_filter:
        filtered = [j for j in filtered if j["category"] in cat_filter]

    # Apply status filter
    if stat_filter:
        filtered = [j for j in filtered if statuses.get(j["id"], "new") in stat_filter]

    if not filtered:
        st.info("Cap oferta trobada amb aquests filtres.")
    else:
        df = pd.DataFrame([{
            "Data": j["first_seen_at"][:10],
            "Títol": j["title"],
            "Empresa": j["company"],
            "Ubicació": j["location"],
            "Categoria": CATEGORY_LABELS.get(j["category"], j["category"]),
            "Font": j["source"],
            "Estat": STATUS_LABELS.get(statuses.get(j["id"], "new"), "🆕 Nou"),
            "URL": j["url"],
        } for j in filtered])

        st.dataframe(
            df,
            column_config={"URL": st.column_config.LinkColumn("Enllaç")},
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Descarregar CSV",
            data=csv,
            file_name=f"ofertes_suissa_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )


# ════════════════════════════════════════════════════════════════
# TAB 3 — CANDIDATURES
# ════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("On ha aplicat l'Arnaud")

    applied_ids = {jid for jid, s in statuses.items() if s == "applied"}
    applied_jobs = [j for j in all_jobs if j["id"] in applied_ids]

    if not applied_jobs:
        st.info("Encara no has marcat cap oferta com aplicada. Fes-ho des de la pestanya 📋 Avui.")
    else:
        st.success(f"{len(applied_jobs)} candidatura(es) enviada(es)")
        for job in applied_jobs:
            col_info, col_revert = st.columns([6, 1])
            with col_info:
                st.markdown(
                    f"**[{job['title']}]({job['url']})** · {job['company']} · 📍{job['location']} · _{job['first_seen_at'][:10]}_"
                )
            with col_revert:
                if st.button("↩️", key=f"rev_{job['id']}", help="Desmarcar"):
                    set_status(job["id"], "new")
                    st.rerun()


# ════════════════════════════════════════════════════════════════
# TAB 4 — CONFIGURACIÓ
# ════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Configuració")

    cfg = load_config()

    # ── Candidate profile ────────────────────────────────────────
    with st.expander("👤 Perfil del candidat", expanded=True):
        candidate = cfg.get("candidate", {})
        candidate["name"] = st.text_input("Nom", value=candidate.get("name", ""))
        candidate["education"] = st.text_input("Formació", value=candidate.get("education", ""))
        candidate["goal"] = st.text_area("Objectiu professional", value=candidate.get("goal", ""), height=80)
        exp_text = "\n".join(candidate.get("experience", []))
        new_exp = st.text_area("Experiències (una per línia)", value=exp_text, height=100)
        candidate["experience"] = [e.strip() for e in new_exp.splitlines() if e.strip()]
        cfg["candidate"] = candidate

    # ── Search settings ──────────────────────────────────────────
    with st.expander("🔍 Cerca"):
        search = cfg.get("search", {})
        locations_text = "\n".join(search.get("locations", []))
        new_locs = st.text_area("Ubicacions (una per línia)", value=locations_text, height=120)
        search["locations"] = [l.strip() for l in new_locs.splitlines() if l.strip()]
        search["hours_old"] = st.number_input(
            "Màxim d'hores d'antiguitat de les ofertes", min_value=12, max_value=168,
            value=search.get("hours_old", 24), step=12
        )
        cfg["search"] = search

    # ── Notifications ─────────────────────────────────────────────
    with st.expander("🔔 Notificacions"):
        notif = cfg.get("notifications", {})
        tg = notif.get("telegram", {})
        tg["enabled"] = st.toggle("Telegram activat", value=tg.get("enabled", False))
        email = notif.get("email", {})
        email["enabled"] = st.toggle("Email activat", value=email.get("enabled", False))
        notif["telegram"] = tg
        notif["email"] = email
        cfg["notifications"] = notif

    if st.button("💾 Desar configuració"):
        save_config(cfg)
        st.success("✅ config.yaml actualitzat!")
        st.info("Fes **git commit + git push** per aplicar els canvis al scraper de GitHub Actions.")

    st.divider()

    # ── Actions ───────────────────────────────────────────────────
    col_pull, col_run = st.columns(2)

    with col_pull:
        st.markdown("**🔄 Actualitzar dades**")
        st.caption("Descarrega les últimes ofertes des de GitHub.")
        if st.button("🔄 git pull"):
            result = subprocess.run(["git", "pull"], capture_output=True, text=True)
            if result.returncode == 0:
                st.success(result.stdout or "Ja estàs al dia!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(result.stderr)

    with col_run:
        st.markdown("**▶️ Llançar cerca ara**")
        st.caption("Executa el scraper al teu ordinador (pot trigar 1-2 minuts).")
        if st.button("▶️ Llançar cerca"):
            with st.spinner("Buscant ofertes..."):
                result = subprocess.run(
                    ["python", "main.py"], capture_output=True, text=True
                )
            if result.returncode == 0:
                st.success("Cerca completada!")
                st.cache_data.clear()
            else:
                st.warning("La cerca ha acabat amb avisos.")
            st.code(result.stdout + result.stderr, language="text")

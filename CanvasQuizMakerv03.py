#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CanvasQuizMaker.py
GUI tool to create Canvas Classic QTI quizzes without coding.
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import xml.etree.ElementTree as ET
import re
import uuid
import zipfile
import io
import html

APP_TITLE = "Canvas QTI Quiz Maker"
VERSION = "3.0"

# ----------------------- Helpers -----------------------

def sanitize_text(s: str) -> str:
    return html.escape(s, quote=False).replace('\n', '<br/>')

def new_ident(prefix="i"):
    return f"{prefix}{uuid.uuid4().hex[:8]}"

def pretty_xml(elem):
    rough = ET.tostring(elem, encoding="utf-8")
    try:
        import xml.dom.minidom as md
        return md.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    except Exception:
        return rough

# ----------------------- QTI Builders -----------------------

def build_qti_item(question):
    q_type = question['type']
    q_id = new_ident("item_")
    item = ET.Element("item", attrib={"ident": q_id, "title": "Question"})
    presentation = ET.SubElement(item, "presentation")

    material = ET.SubElement(presentation, "material")
    ET.SubElement(material, "mattext", {"texttype": "text/html"}).text = sanitize_text(question['text'])

    if q_type in ("MC", "TF"):
        resp = ET.SubElement(presentation, "response_lid", {"ident": "response1", "rcardinality": "Single"})
        rc = ET.SubElement(resp, "render_choice")
        labels = []
        for idx, opt in enumerate(question['answers']):
            lab_id = f"L{idx+1}"
            labels.append(lab_id)
            rlab = ET.SubElement(rc, "response_label", {"ident": lab_id})
            mat = ET.SubElement(rlab, "material")
            ET.SubElement(mat, "mattext", {"texttype": "text/html"}).text = sanitize_text(opt)

        res = ET.SubElement(item, "resprocessing")
        outcomes = ET.SubElement(res, "outcomes")
        ET.SubElement(outcomes, "decvar", {"maxvalue": "100", "minvalue": "0", "varname": "SCORE", "vartype": "Decimal"})
        corr_lab = f"L{(question['correct'][0] if isinstance(question['correct'], list) else question['correct']) + 1}"
        rcorr = ET.SubElement(res, "respcondition", {"title": "correct", "continue": "No"})
        cond = ET.SubElement(rcorr, "conditionvar")
        ET.SubElement(cond, "varequal", {"respident": "response1"}).text = corr_lab
        ET.SubElement(rcorr, "setvar", {"varname": "SCORE", "action": "Set"}).text = "100"

        rinc = ET.SubElement(res, "respcondition", {"title": "incorrect", "continue": "Yes"})
        condi = ET.SubElement(rinc, "conditionvar")
        other = ET.SubElement(condi, "other")
        ET.SubElement(rinc, "setvar", {"varname": "SCORE", "action": "Set"}).text = "0"

    elif q_type == "MR":
        resp = ET.SubElement(presentation, "response_lid", {"ident": "response1", "rcardinality": "Multiple"})
        rc = ET.SubElement(resp, "render_choice")
        labels = []
        for idx, opt in enumerate(question['answers']):
            lab_id = f"L{idx+1}"
            labels.append(lab_id)
            rlab = ET.SubElement(rc, "response_label", {"ident": lab_id})
            mat = ET.SubElement(rlab, "material")
            ET.SubElement(mat, "mattext", {"texttype": "text/html"}).text = sanitize_text(opt)

        correct_set = {f"L{ix+1}" for ix in question['correct']}
        res = ET.SubElement(item, "resprocessing")
        outcomes = ET.SubElement(res, "outcomes")
        ET.SubElement(outcomes, "decvar", {"maxvalue": "100", "minvalue": "0", "varname": "SCORE", "vartype": "Decimal"})

        r_ok = ET.SubElement(res, "respcondition", {"title": "correct", "continue": "No"})
        cv = ET.SubElement(r_ok, "conditionvar")
        andnode = ET.SubElement(cv, "and")
        for lab in correct_set:
            ET.SubElement(andnode, "varequal", {"respident": "response1"}).text = lab
        incorrect = set(labels) - correct_set
        if incorrect:
            notnode = ET.SubElement(andnode, "not")
            orbad = ET.SubElement(notnode, "or")
            for lab in incorrect:
                ET.SubElement(orbad, "varequal", {"respident": "response1"}).text = lab
        ET.SubElement(r_ok, "setvar", {"varname": "SCORE", "action": "Set"}).text = "100"

        r_bad = ET.SubElement(res, "respcondition", {"title": "incorrect", "continue": "Yes"})
        cvb = ET.SubElement(r_bad, "conditionvar")
        ET.SubElement(cvb, "other")
        ET.SubElement(r_bad, "setvar", {"varname": "SCORE", "action": "Set"}).text = "0"

    elif q_type == "ESSAY":
        ET.SubElement(presentation, "response_str", {"ident": "response1", "rcardinality": "Single"})

    elif q_type == "SHORT_ANSWER":
        resp = ET.SubElement(presentation, "response_str", {"ident": "response1", "rcardinality": "Single"})
        res = ET.SubElement(item, "resprocessing")
        outcomes = ET.SubElement(res, "outcomes")
        ET.SubElement(outcomes, "decvar", {"maxvalue": "100", "minvalue": "0", "varname": "SCORE", "vartype": "Decimal"})
        r_ok = ET.SubElement(res, "respcondition", {"title": "correct", "continue": "No"})
        cv = ET.SubElement(r_ok, "conditionvar")
        ornode = ET.SubElement(cv, "or")
        for ans in question.get('short_answers', []):
            ET.SubElement(ornode, "varequal", {"respident": "response1", "case": "No"}).text = ans
        ET.SubElement(r_ok, "setvar", {"varname": "SCORE", "action": "Set"}).text = "100"
        r_bad = ET.SubElement(res, "respcondition", {"title": "incorrect", "continue": "Yes"})
        ET.SubElement(ET.SubElement(r_bad, "conditionvar"), "other")
        ET.SubElement(r_bad, "setvar", {"varname": "SCORE", "action": "Set"}).text = "0"

    elif q_type == "NUMERIC":
        presentation_num = ET.SubElement(presentation, "response_num", {"ident": "response1", "rcardinality": "Single"})
        res = ET.SubElement(item, "resprocessing")
        outcomes = ET.SubElement(res, "outcomes")
        ET.SubElement(outcomes, "decvar", {"maxvalue": "100", "minvalue": "0", "varname": "SCORE", "vartype": "Decimal"})
        r_ok = ET.SubElement(res, "respcondition", {"title": "correct", "continue": "No"})
        cv = ET.SubElement(r_ok, "conditionvar")
        num = question.get('numeric', {})
        if 'min' in num and 'max' in num:
            gte = ET.SubElement(cv, "vargte", {"respident": "response1"})
            gte.text = str(num['min'])
            lte = ET.SubElement(cv, "varlte", {"respident": "response1"})
            lte.text = str(num['max'])
        else:
            val = float(num.get('value', 0))
            tol = float(num.get('tolerance', 0))
            if tol > 0:
                gte = ET.SubElement(cv, "vargte", {"respident": "response1"})
                gte.text = str(val - tol)
                lte = ET.SubElement(cv, "varlte", {"respident": "response1"})
                lte.text = str(val + tol)
            else:
                ET.SubElement(cv, "varequal", {"respident": "response1"}).text = str(val)
        ET.SubElement(r_ok, "setvar", {"varname": "SCORE", "action": "Set"}).text = "100"
        r_bad = ET.SubElement(res, "respcondition", {"title": "incorrect", "continue": "Yes"})
        ET.SubElement(ET.SubElement(r_bad, "conditionvar"), "other")
        ET.SubElement(r_bad, "setvar", {"varname": "SCORE", "action": "Set"}).text = "0"

    elif q_type == "MATCHING":
        resp = ET.SubElement(presentation, "response_lid", {"ident": "response1", "rcardinality": "Multiple"})
        rm = ET.SubElement(resp, "render_match")
        left_ids, right_ids = [], []
        for idx, (left, right) in enumerate(question.get('pairs', []), start=1):
            lid = f"S{idx}"
            rid = f"T{idx}"
            left_ids.append((lid, left))
            right_ids.append((rid, right))
        for lid, text in left_ids:
            rl = ET.SubElement(rm, "response_label", {"ident": lid})
            mat = ET.SubElement(rl, "material")
            ET.SubElement(mat, "mattext", {"texttype": "text/html"}).text = sanitize_text(text)
        for rid, text in right_ids:
            rl = ET.SubElement(rm, "response_label", {"ident": rid})
            mat = ET.SubElement(rl, "material")
            ET.SubElement(mat, "mattext", {"texttype": "text/html"}).text = sanitize_text(text)

        res = ET.SubElement(item, "resprocessing")
        outcomes = ET.SubElement(res, "outcomes")
        ET.SubElement(outcomes, "decvar", {"maxvalue": "100", "minvalue": "0", "varname": "SCORE", "vartype": "Decimal"})
        r_ok = ET.SubElement(res, "respcondition", {"title": "correct", "continue": "No"})
        cv = ET.SubElement(r_ok, "conditionvar")
        andnode = ET.SubElement(cv, "and")
        for idx in range(1, len(question['pairs'])+1):
            ET.SubElement(andnode, "varequal", {"respident": "response1"}).text = f"S{idx} T{idx}"
        ET.SubElement(r_ok, "setvar", {"varname": "SCORE", "action": "Set"}).text = "100"
        r_bad = ET.SubElement(res, "respcondition", {"title": "incorrect", "continue": "Yes"})
        ET.SubElement(ET.SubElement(r_bad, "conditionvar"), "other")
        ET.SubElement(r_bad, "setvar", {"varname": "SCORE", "action": "Set"}).text = "0"

    imd = ET.SubElement(item, "itemmetadata")
    md = ET.SubElement(imd, "qtimetadata")
    f = ET.SubElement(md, "qtimetadatafield")
    ET.SubElement(f, "fieldlabel").text = "qmd_itemtype"
    ET.SubElement(f, "fieldentry").text = q_type
    f2 = ET.SubElement(md, "qtimetadatafield")
    ET.SubElement(f2, "fieldlabel").text = "points_possible"
    ET.SubElement(f2, "fieldentry").text = str(question['points'])

    return item

def build_assessment_xml(title, questions):
    root = ET.Element("questestinterop")
    assessment = ET.SubElement(root, "assessment", {"ident": new_ident("assess_"), "title": title})
    total_points = sum(float(q["points"]) for q in questions)
    mdl = ET.SubElement(assessment, "qtimetadata")
    f = ET.SubElement(mdl, "qtimetadatafield")
    ET.SubElement(f, "fieldlabel").text = "canvas_exporter_version"
    ET.SubElement(f, "fieldentry").text = "QTI-1.2"
    f2 = ET.SubElement(mdl, "qtimetadatafield")
    ET.SubElement(f2, "fieldlabel").text = "points_possible"
    ET.SubElement(f2, "fieldentry").text = str(total_points)

    section = ET.SubElement(assessment, "section", {"ident": "root_section"})
    for q in questions:
        section.append(build_qti_item(q))
    return pretty_xml(root)

def build_manifest_xml():
    pkg = ET.Element("manifest", {
        "identifier": new_ident("MANIFEST_"),
        "xmlns": "http://www.imsglobal.org/xsd/imscp_v1p1",
        "xmlns:imsmd": "http://www.imsglobal.org/xsd/imsmd_v1p2",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://www.imsglobal.org/xsd/imscp_v1p1 imscp_v1p1.xsd http://www.imsglobal.org/xsd/imsmd_v1p2 imsmd_v1p2p2.xsd"
    })
    resources = ET.SubElement(pkg, "resources")
    ET.SubElement(resources, "resource", {
        "identifier": "quiz1",
        "type": "imsqti_xmlv1p2",
        "href": "quiz.xml"
    })
    return pretty_xml(pkg)

# ----------------------- GUI -----------------------

class QuestionEditor(ttk.Toplevel):
    def __init__(self, master, save_callback):
        super().__init__(master)
        self.title("Add / Edit Question")
        self.save_callback = save_callback
        self.geometry("750x680")
        self.resizable(True, True)

        self.var_type = tk.StringVar(value="MC")
        self.var_points = tk.StringVar(value="1")
        self.var_text = ttk.Text(self, height=6, wrap="word", font=("Helvetica", 11))

        frm_top = ttk.Frame(self, padding=10)
        frm_top.pack(fill="x")
        ttk.Label(frm_top, text="Type:", font=("Helvetica", 10, "bold")).pack(side="left")
        ttk.Combobox(frm_top, textvariable=self.var_type, values=[
            "MC","MR","TF","SHORT_ANSWER","NUMERIC","ESSAY","MATCHING"
        ], state="readonly", width=16).pack(side="left", padx=10)
        ttk.Label(frm_top, text="Points:", font=("Helvetica", 10, "bold")).pack(side="left", padx=(16,0))
        ttk.Entry(frm_top, textvariable=self.var_points, width=8).pack(side="left", padx=10)

        frm_q = ttk.Labelframe(self, text="Question Text (HTML allowed)", padding=10, bootstyle="info")
        frm_q.pack(fill="both", expand=False, padx=10, pady=5)
        self.var_text.pack(fill="both", expand=True)

        self.dynamic = ttk.Labelframe(self, text="Options / Parameters", padding=10, bootstyle="primary")
        self.dynamic.pack(fill="both", expand=True, padx=10, pady=5)
        self.inner = ttk.Frame(self.dynamic)
        self.inner.pack(fill="both", expand=True)
        self.dynamic_widgets = []
        self.render_dynamic("MC")

        frm_btn = ttk.Frame(self, padding=10)
        frm_btn.pack(fill="x")
        ttk.Button(frm_btn, text="Cancel", command=self.destroy, bootstyle="secondary-outline").pack(side="right", padx=5)
        ttk.Button(frm_btn, text="Save Question", command=self.on_save, bootstyle="success").pack(side="right")

        self.var_type.trace_add('write', lambda *args: self.render_dynamic(self.var_type.get()))

    def clear_dynamic(self):
        for w in self.dynamic_widgets:
            w.destroy()
        self.dynamic_widgets = []

    def render_dynamic(self, qtype):
        self.clear_dynamic()
        if qtype in ("MC","MR","TF"):
            self.opt_vars = []
            default_opts = ["True","False"] if qtype=="TF" else ["Option A","Option B","Option C","Option D"]
            frm = ttk.Frame(self.inner)
            frm.pack(fill="x", pady=5)
            self.dynamic_widgets.append(frm)

            ttk.Label(frm, text="Options (Check box to mark correct):", font=("Helvetica", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
            self.correct_vars = []
            for i, txt in enumerate(default_opts):
                ov = tk.StringVar(value=txt)
                cv = tk.BooleanVar(value=(i==1 if qtype=="TF" else False))
                self.opt_vars.append(ov); self.correct_vars.append(cv)
                ttk.Checkbutton(frm, variable=cv, bootstyle="success-round-toggle").grid(row=i+1, column=0, padx=10, pady=5, sticky="w")
                ttk.Entry(frm, textvariable=ov, width=65).grid(row=i+1, column=1, padx=5, pady=5, sticky="w")

            if qtype in ("MC","MR"):
                btnf = ttk.Frame(self.inner)
                btnf.pack(anchor="w", pady=10)
                self.dynamic_widgets.append(btnf)
                ttk.Button(btnf, text="+ Add Option", command=self.add_option, bootstyle="info-outline").pack(side="left")
                ttk.Button(btnf, text="− Remove Last", command=self.remove_option, bootstyle="danger-outline").pack(side="left", padx=10)

        elif qtype == "SHORT_ANSWER":
            ttk.Label(self.inner, text="Acceptable Answers (one per line, case-insensitive):", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=5)
            self.txt_short = ttk.Text(self.inner, height=8, font=("Helvetica", 11))
            self.txt_short.pack(fill="x", pady=5)
            self.dynamic_widgets += [self.txt_short]

        elif qtype == "NUMERIC":
            fr = ttk.Frame(self.inner)
            fr.pack(fill="x", pady=10)
            self.dynamic_widgets.append(fr)
            self.num_mode = tk.StringVar(value="exact")
            ttk.Radiobutton(fr, text="Exact ± Tolerance", variable=self.num_mode, value="exact", bootstyle="info").grid(row=0, column=0, sticky="w", padx=10)
            ttk.Radiobutton(fr, text="Range [min, max]", variable=self.num_mode, value="range", bootstyle="info").grid(row=0, column=1, sticky="w")
            
            fr2 = ttk.Frame(self.inner)
            fr2.pack(fill="x", pady=10)
            self.dynamic_widgets.append(fr2)
            self.var_num_value = tk.StringVar()
            self.var_num_tol = tk.StringVar(value="0")
            self.var_num_min = tk.StringVar()
            self.var_num_max = tk.StringVar()
            
            ttk.Label(fr2, text="Value:").grid(row=0,column=0,sticky="e", pady=5)
            ttk.Entry(fr2, textvariable=self.var_num_value, width=15).grid(row=0,column=1, padx=10)
            ttk.Label(fr2, text="Tolerance:").grid(row=0,column=2,sticky="e")
            ttk.Entry(fr2, textvariable=self.var_num_tol, width=15).grid(row=0,column=3, padx=10)
            
            ttk.Label(fr2, text="Min:").grid(row=1,column=0,sticky="e", pady=5)
            ttk.Entry(fr2, textvariable=self.var_num_min, width=15).grid(row=1,column=1, padx=10)
            ttk.Label(fr2, text="Max:").grid(row=1,column=2,sticky="e")
            ttk.Entry(fr2, textvariable=self.var_num_max, width=15).grid(row=1,column=3, padx=10)

        elif qtype == "ESSAY":
            ttk.Label(self.inner, text="No additional settings required for manual grading.", font=("Helvetica", 10, "italic")).pack(anchor="w", pady=10)

        elif qtype == "MATCHING":
            ttk.Label(self.inner, text="Matching Pairs (Left ↔ Right):", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=5)
            self.match_frame = ttk.Frame(self.inner)
            self.match_frame.pack(fill="x")
            self.rows = []
            self.add_match_row()
            btnf = ttk.Frame(self.inner)
            btnf.pack(anchor="w", pady=10)
            self.dynamic_widgets += [self.match_frame, btnf]
            ttk.Button(btnf, text="+ Add Pair", command=self.add_match_row, bootstyle="info-outline").pack(side="left")
            ttk.Button(btnf, text="− Remove Last", command=self.remove_match_row, bootstyle="danger-outline").pack(side="left", padx=10)

    def add_option(self):
        frm = self.dynamic.winfo_children()[0]
        idx = len(self.opt_vars)
        ov = tk.StringVar(value=f"Option {idx+1}")
        cv = tk.BooleanVar(False)
        self.opt_vars.append(ov); self.correct_vars.append(cv)
        row = idx+1
        ttk.Checkbutton(frm, variable=cv, bootstyle="success-round-toggle").grid(row=row, column=0, padx=10, pady=5, sticky="w")
        ttk.Entry(frm, textvariable=ov, width=65).grid(row=row, column=1, padx=5, pady=5, sticky="w")

    def remove_option(self):
        if len(self.opt_vars) > 2:
            self.opt_vars.pop()
            self.correct_vars.pop()
            frm = self.dynamic.winfo_children()[0]
            for w in frm.grid_slaves(row=len(self.opt_vars)+1):
                w.destroy()

    def add_match_row(self):
        r = ttk.Frame(self.match_frame)
        vL = tk.StringVar(); vR = tk.StringVar()
        ttk.Entry(r, textvariable=vL, width=35).pack(side="left", padx=5, pady=5)
        ttk.Label(r, text="↔", font=("Helvetica", 12, "bold")).pack(side="left", padx=5)
        ttk.Entry(r, textvariable=vR, width=35).pack(side="left", padx=5, pady=5)
        r.pack(anchor="w")
        self.rows.append((r, vL, vR))

    def remove_match_row(self):
        if self.rows:
            r, vL, vR = self.rows.pop()
            r.destroy()

    def on_save(self):
        try:
            q = {
                "type": self.var_type.get(),
                "points": float(self.var_points.get()),
                "text": self.var_text.get("1.0","end").strip()
            }
            if not q["text"]:
                messagebox.showerror("Missing text","Please enter the question text.")
                return

            qt = q["type"]
            if qt in ("MC","MR","TF"):
                answers = [v.get().strip() for v in getattr(self, "opt_vars", [])]
                correct = [i for i, cv in enumerate(getattr(self, "correct_vars", [])) if cv.get()]
                if qt == "TF" and len(answers) != 2:
                    messagebox.showerror("True/False","TF requires exactly two options.")
                    return
                if not answers or any(a=="" for a in answers):
                    messagebox.showerror("Options","Please fill all options.")
                    return
                if qt == "MC" and len(correct) != 1:
                    messagebox.showerror("Correct answer","MC needs exactly one correct option.")
                    return
                if qt in ("MR","TF") and len(correct) < 1:
                    messagebox.showerror("Correct answer","Select at least one correct option.")
                    return
                q["answers"] = answers
                q["correct"] = correct

            elif qt == "SHORT_ANSWER":
                raw = self.txt_short.get("1.0","end").strip()
                alts = [s.strip() for s in raw.splitlines() if s.strip()]
                if not alts:
                    messagebox.showerror("Answers","Add at least one acceptable answer.")
                    return
                q["short_answers"] = alts

            elif qt == "NUMERIC":
                mode = self.num_mode.get()
                if mode == "exact":
                    val = self.var_num_value.get().strip()
                    tol = self.var_num_tol.get().strip() or "0"
                    if val == "":
                        messagebox.showerror("Numeric","Enter a value.")
                        return
                    q["numeric"] = {"value": float(val), "tolerance": float(tol)}
                else:
                    vmin = self.var_num_min.get().strip()
                    vmax = self.var_num_max.get().strip()
                    if vmin == "" or vmax == "":
                        messagebox.showerror("Numeric","Enter min and max.")
                        return
                    q["numeric"] = {"min": float(vmin), "max": float(vmax)}

            elif qt == "MATCHING":
                pairs = []
                for _, vL, vR in self.rows:
                    L = vL.get().strip(); R = vR.get().strip()
                    if L and R:
                        pairs.append((L,R))
                if len(pairs) < 1:
                    messagebox.showerror("Matching","Add at least one pair.")
                    return
                q["pairs"] = pairs

            self.save_callback(q)
            self.destroy()
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))

class App(ttk.Window):
    def __init__(self):
        super().__init__(title=f"{APP_TITLE} v{VERSION}", themename="flatly", size=(1000, 700))
        self.questions = []

        top = ttk.Frame(self, padding=20)
        top.pack(fill="x")
        ttk.Label(top, text="Quiz Title:", font=("Helvetica", 12, "bold")).pack(side="left")
        self.var_title = tk.StringVar(value="Canvas Quiz Export")
        ttk.Entry(top, textvariable=self.var_title, width=50, font=("Helvetica", 11)).pack(side="left", padx=15)

        mid = ttk.Frame(self, padding=20)
        mid.pack(fill="both", expand=True)
        
        self.tree = ttk.Treeview(mid, columns=("type","points","text"), show="headings", selectmode="browse", bootstyle="primary")
        self.tree.heading("type", text="Type")
        self.tree.heading("points", text="Points")
        self.tree.heading("text", text="Question (Preview)")
        self.tree.column("type", width=120, anchor="center")
        self.tree.column("points", width=80, anchor="center")
        self.tree.column("text", width=650)
        self.tree.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview, bootstyle="round")
        self.tree.configure(yscroll=sb.set)
        sb.pack(side="right", fill="y", padx=(5,0))

        btns = ttk.Frame(self, padding=20)
        btns.pack(fill="x")
        ttk.Button(btns, text="+ Add Question", command=self.add_question, bootstyle="success").pack(side="left")
        ttk.Button(btns, text="📋 Paste Text", command=self.bulk_import, bootstyle="info").pack(side="left", padx=10)
        ttk.Button(btns, text="✎ Edit", command=self.edit_selected, bootstyle="warning").pack(side="left", padx=10)
        ttk.Button(btns, text="🗑 Remove", command=self.remove_selected, bootstyle="danger").pack(side="left", padx=10)
        ttk.Button(btns, text="⬇ Export QTI (.zip)", command=self.export_qti, bootstyle="primary").pack(side="right")

    def add_question(self):
        def on_save(q):
            self.questions.append(q)
            self.refresh()
        QuestionEditor(self, on_save)

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Edit", "Select a question to edit.")
            return
        idx = int(sel[0])
        q = self.questions[idx]

        def on_save(new_q):
            self.questions[idx] = new_q
            self.refresh()

        ed = QuestionEditor(self, on_save)
        ed.var_type.set(q["type"])
        ed.var_points.set(str(q["points"]))
        ed.var_text.insert("1.0", q["text"])

        ed.render_dynamic(q["type"])
        if q["type"] in ("MC","MR","TF"):
            for i in range(len(q["answers"]) - len(getattr(ed, "opt_vars", []))):
                ed.add_option()
            for i, opt in enumerate(q["answers"]):
                ed.opt_vars[i].set(opt)
                ed.correct_vars[i].set(i in q["correct"])
        elif q["type"] == "SHORT_ANSWER":
            ed.txt_short.insert("1.0", "\n".join(q.get("short_answers", [])))
        elif q["type"] == "NUMERIC":
            num = q.get("numeric", {})
            if "min" in num:
                ed.num_mode.set("range")
                ed.var_num_min.set(str(num["min"]))
                ed.var_num_max.set(str(num["max"]))
            else:
                ed.num_mode.set("exact")
                ed.var_num_value.set(str(num.get("value","")))
                ed.var_num_tol.set(str(num.get("tolerance","0")))
        elif q["type"] == "MATCHING":
            for _ in range(len(getattr(ed, "rows", []))):
                ed.remove_match_row()
            for L,R in q.get("pairs", []):
                ed.add_match_row()
                ed.rows[-1][1].set(L)
                ed.rows[-1][2].set(R)

    def remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self.questions.pop(idx)
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for i, q in enumerate(self.questions):
            text_preview = re.sub(r'<.*?>','', q['text'])
            if len(text_preview) > 120:
                text_preview = text_preview[:117] + "..."
            self.tree.insert("", "end", iid=str(i), values=(q["type"], q["points"], text_preview))

    def bulk_import(self):
        win = ttk.Toplevel(self)
        win.title("Bulk Import Questions")
        win.geometry("650x550")

        instructions = (
            "Paste multiple choice questions below. Example format:\n\n"
            "Question: Who painted the murals in the Hospicio Cabañas?\n"
            "A. Diego Rivera\n"
            "B. David Alfaro Siqueiros\n"
            "C. José Clemente Orozco\n"
            "Answer: C."
        )
        ttk.Label(win, text=instructions, font=("Helvetica", 10)).pack(anchor="w", padx=20, pady=15)
        
        text_area = ttk.Text(win, wrap="word", height=15, font=("Helvetica", 11))
        text_area.pack(fill="both", expand=True, padx=20, pady=5)

        def process():
            raw_text = text_area.get("1.0", "end")
            parsed_questions = self.parse_text_format(raw_text)
            if parsed_questions:
                self.questions.extend(parsed_questions)
                self.refresh()
                messagebox.showinfo("Success", f"Successfully imported {len(parsed_questions)} questions.")
                win.destroy()
            else:
                messagebox.showerror("Parse Error", "No valid questions found. Please check your formatting.")

        ttk.Button(win, text="Import Text", command=process, bootstyle="success").pack(pady=15)

    def parse_text_format(self, raw_text):
        results = []
        blocks = re.split(r'(?i)Question:\s*', raw_text)
        
        for block in blocks:
            if not block.strip(): 
                continue
            
            lines = block.strip().split('\n')
            q_text = []
            options = []
            letters = []
            ans_idx = -1

            for line in lines:
                line = line.strip()
                if not line: continue

                opt_match = re.match(r'^([A-Za-z])[\.\)]\s+(.*)', line)
                ans_match = re.match(r'(?i)^Answer:\s*([A-Za-z])\.?', line)

                if ans_match:
                    ans_char = ans_match.group(1).upper()
                    if ans_char in letters:
                        ans_idx = letters.index(ans_char)
                elif opt_match:
                    letters.append(opt_match.group(1).upper())
                    options.append(opt_match.group(2).strip())
                else:
                    q_text.append(line)

            if q_text and options and ans_idx != -1:
                results.append({
                    "type": "MC",
                    "points": 1.0,
                    "text": " ".join(q_text).strip(),
                    "answers": options,
                    "correct": [ans_idx]
                })
        return results

    def export_qti(self):
        if not self.questions:
            messagebox.showerror("Export", "Add at least one question.")
            return
        title = self.var_title.get().strip() or "Canvas Quiz"
        try:
            assessment_xml = build_assessment_xml(title, self.questions)
            manifest_xml = build_manifest_xml()

            mem = io.BytesIO()
            with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("imsmanifest.xml", manifest_xml)
                z.writestr("quiz.xml", assessment_xml)
            mem.seek(0)

            default_name = f"{re.sub(r'[^A-Za-z0-9_-]+','_', title)}.zip"
            path = filedialog.asksaveasfilename(
                title="Save QTI zip",
                defaultextension=".zip",
                initialfile=default_name,
                filetypes=[("QTI zip", "*.zip"), ("All files", "*.*")]
            )
            if not path: return
            with open(path, "wb") as f:
                f.write(mem.read())

            messagebox.showinfo("Exported", "QTI package exported.\nCanvas: Settings → Import Course Content → QTI .zip file.")
        except Exception as e:
            messagebox.showerror("Export error", str(e))

if __name__ == "__main__":
    app = App()
    app.place_window_center()
    app.mainloop()
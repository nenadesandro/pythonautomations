import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import re
import smtplib
from email.message import EmailMessage

# ====== CONFIG IA (opcional) ======
USE_AI = True
OPENAI_API_KEY = "MY_API_KEY"
# ====== EMAIL CONFIG ======
SENDER_EMAIL = "pilarlb99@gmail.com"
APP_PASSWORD = "xjrg ggyu dwhe XXX"   # contraseña de aplicación (no tu password normal)

# ====== LIMPIEZA TITULO ======
def clean_title(title):
    title = str(title)
    title = re.sub(r"Watched ", "", title)
    title = re.sub(r"Has visto ", "", title)
    return title.strip()

# ====== CLASIFICACION ======
def classify_video(title):
    title = title.lower()

    if any(x in title for x in ["python","ai","data","coding","program"]):
        return "Tech"
    if any(x in title for x in ["gym","fitness","workout"]):
        return "Fitness"
    if any(x in title for x in ["podcast","interview"]):
        return "Podcast"
    if any(x in title for x in ["music","song"]):
        return "Music"
    if any(x in title for x in ["news"]):
        return "News"

    return "Other"

# ====== IA ANALISIS ======
def ai_analysis(text_summary):
    if not USE_AI:
        return "AI analysis disabled."

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    Analyze this YouTube consumption summary and give short behavioral insights:

    {text_summary}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    return response.choices[0].message.content

# ====== EMAIL SMTP ======
def send_email_smtp(to_email, subject, body, attachments=[]):
    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    for file in attachments:
        with open(file, "rb") as f:
            file_data = f.read()
            file_name = os.path.basename(file)
            msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=file_name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SENDER_EMAIL, APP_PASSWORD)
        smtp.send_message(msg)

# ====== PROCESAMIENTO ======
def process_file(filepath, email_to):

    df = pd.read_csv(filepath)

    if "title" not in df.columns or "time" not in df.columns:
        messagebox.showerror("Error","CSV must contain columns: title, time")
        return

    df["title"] = df["title"].apply(clean_title)
    df["datetime"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["datetime"])

    # ultimo mes
    last_month = datetime.now() - timedelta(days=30)
    df = df[df["datetime"] >= last_month]

    if df.empty:
        messagebox.showinfo("Info","No videos last month")
        return

    # categorias
    df["category"] = df["title"].apply(classify_video)

    ranking_video = df["title"].value_counts()
    ranking_cat = df["category"].value_counts()

    # guardar csv limpio
    csv_path = "youtube_last_month.csv"
    df.to_csv(csv_path, index=False)

    # ===== GRAFICOS =====
    plt.figure()
    ranking_cat.plot(kind="bar")
    plt.title("Videos by Category")
    plt.tight_layout()
    cat_img = "cat_chart.png"
    plt.savefig(cat_img)

    plt.figure()
    ranking_video.head(10).plot(kind="barh")
    plt.title("Top 10 Videos")
    plt.tight_layout()
    vid_img = "top_videos.png"
    plt.savefig(vid_img)

    # ===== RESUMEN =====
    summary = f"""
Total videos watched: {len(df)}
Top category: {ranking_cat.idxmax()}
Top video: {ranking_video.idxmax()}
"""

    ai_text = ai_analysis(summary)

    body = f"""
YouTube Analytics Last Month

{summary}

AI Insight:
{ai_text}
"""

    send_email_smtp(
        email_to,
        "YouTube Monthly Analytics",
        body,
        attachments=[csv_path, cat_img, vid_img]
    )

    messagebox.showinfo("Done","Report sent successfully!")

# ====== GUI ======
def launch_gui():
    root = tk.Tk()
    root.title("YouTube Analytics AI")
    root.geometry("420x260")

    filepath_var = tk.StringVar()
    email_var = tk.StringVar()

    def browse():
        path = filedialog.askopenfilename(filetypes=[("CSV","*.csv")])
        filepath_var.set(path)

    def run():
        if not filepath_var.get():
            messagebox.showerror("Error","Select CSV file")
            return
        if not email_var.get():
            messagebox.showerror("Error","Enter email")
            return

        process_file(filepath_var.get(), email_var.get())

    tk.Label(root, text="Select YouTube CSV").pack(pady=5)
    tk.Entry(root, textvariable=filepath_var, width=45).pack()
    tk.Button(root, text="Browse", command=browse).pack(pady=5)

    tk.Label(root, text="Send report to email").pack(pady=5)
    tk.Entry(root, textvariable=email_var, width=35).pack()

    tk.Button(root, text="Generate & Send Report", bg="black", fg="white", command=run).pack(pady=20)

    root.mainloop()

# ===== RUN =====
launch_gui()

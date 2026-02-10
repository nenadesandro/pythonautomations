import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import json
from datetime import datetime
import requests

SCHEDULE_FILE = "city_schedule.json"
WEATHER_API_KEY = "8181250368da60c03257ac4abc0fea59"

# ------------------ STYLE ------------------
BG_COLOR = "#ffe6f0"
PRIMARY = "#ff4da6"
SECONDARY = "#ff99cc"
TEXT = "#4a004d"
FONT = ("Roboto", 11)
TITLE_FONT = ("Roboto", 16, "bold")

# ------------------ JSON ------------------
def load_schedule():
    with open(SCHEDULE_FILE, "r") as f:
        return json.load(f)

def save_schedule(data):
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ------------------ FILE LOADER ------------------
def browse_csv(label_widget):
    path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if path:
        label_widget.config(text=path)
        return path
    return None

# ------------------ OVERLAP ------------------
def check_overlaps(file_path, output_box):
    try:
        df = pd.read_csv(file_path)
        df["departure_datetime"] = pd.to_datetime(df["departure_datetime"])
        df["arrival_datetime"] = pd.to_datetime(df["arrival_datetime"])

        df = df.sort_values("departure_datetime")
        overlaps = []

        for i in range(len(df) - 1):
            if df.iloc[i+1]["departure_datetime"] < df.iloc[i]["arrival_datetime"]:
                overlaps.append(
                    f"Overlap between row {i} and {i+1} | "
                    f"{df.iloc[i]['city_of_origin']} -> {df.iloc[i]['city_of_destination']}"
                )

        output_box.delete("1.0", tk.END)

        if overlaps:
            output_box.insert(tk.END, "❌ OVERLAPS DETECTED\n\n")
            for o in overlaps:
                output_box.insert(tk.END, o + "\n")
        else:
            output_box.insert(tk.END, "✅ No overlaps detected")

    except Exception as e:
        messagebox.showerror("Error", str(e))

# ------------------ CITY STATUS ------------------
def run_city_check(file_path, output_box):
    try:
        df = pd.read_csv(file_path)
        df["arrival_datetime"] = pd.to_datetime(df["arrival_datetime"])
        schedule = load_schedule()

        results = []
        for _, row in df.iterrows():
            city = row["city_of_destination"]
            dt_obj = row["arrival_datetime"]

            weekday = dt_obj.strftime("%A").lower()
            time_str = dt_obj.strftime("%H:%M")
            date_str = dt_obj.strftime("%Y-%m-%d")

            if city not in schedule["cities"]:
                results.append(f"{city}: not found")
                continue

            city_data = schedule["cities"][city]
            open_status = "Closed"

            for ex in city_data["exceptions"]:
                if ex["date"] == date_str:
                    if ex["open"] <= time_str <= ex["close"]:
                        open_status = "Open (exception)"
                    else:
                        open_status = f"Closed ({ex['reason']})"

            if open_status == "Closed":
                if weekday in city_data["regular_hours"]:
                    o, c = city_data["regular_hours"][weekday]
                    if o <= time_str <= c:
                        open_status = "Open"

            results.append(f"{city} {dt_obj} -> {open_status}")

        output_box.delete("1.0", tk.END)
        for r in results:
            output_box.insert(tk.END, r + "\n")

    except Exception as e:
        messagebox.showerror("Error", str(e))

# ------------------ WEATHER ------------------
def check_weather(file_path, output_box):
    try:
        df = pd.read_csv(file_path)
        df["departure_datetime"] = pd.to_datetime(df["departure_datetime"])
        df["arrival_datetime"] = pd.to_datetime(df["arrival_datetime"])

        output_box.delete("1.0", tk.END)

        for _, row in df.iterrows():
            city = row["city_of_destination"]
            date = row["arrival_datetime"]

            url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric"
            res = requests.get(url).json()

            rain = False
            for item in res.get("list", []):
                forecast_time = datetime.fromtimestamp(item["dt"])
                if forecast_time.date() == date.date():
                    if "rain" in item["weather"][0]["main"].lower():
                        rain = True
                        break

            if rain:
                output_box.insert(tk.END, f"⚠ Rain expected in {city} on {date.date()}\n")
            else:
                output_box.insert(tk.END, f"✅ No rain risk {city} {date.date()}\n")

    except Exception as e:
        messagebox.showerror("Weather error", str(e))

# ------------------ UI ------------------
root = tk.Tk()
root.title("Ticket Assistant")
root.geometry("950x650")
root.configure(bg=BG_COLOR)

style = ttk.Style()
style.theme_use("default")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

# ------------------ TAB 1
tab1 = tk.Frame(notebook, bg=BG_COLOR)
notebook.add(tab1, text="Welcome")

tk.Label(tab1, text="Ticket Assistant", font=TITLE_FONT, bg=BG_COLOR, fg=PRIMARY).pack(pady=30)
tk.Label(tab1, text="Validate logistics and detect risks", font=FONT, bg=BG_COLOR).pack()

# ------------------ TAB 2 OVERLAP
tab2 = tk.Frame(notebook, bg=BG_COLOR)
notebook.add(tab2, text="Overlap validator")

file_label1 = tk.Label(tab2, text="No file selected", bg=BG_COLOR)
file_label1.pack(pady=5)

def load_overlap():
    path = browse_csv(file_label1)
    if path:
        check_overlaps(path, overlap_output)

tk.Button(tab2, text="Browse CSV", bg=PRIMARY, fg="white", command=load_overlap).pack(pady=10)

overlap_output = tk.Text(tab2, height=20, width=100, bg="#fff0f6")
overlap_output.pack(pady=10)

# ------------------ TAB 3 CITY
tab3 = tk.Frame(notebook, bg=BG_COLOR)
notebook.add(tab3, text="City status")

file_label2 = tk.Label(tab3, text="No file selected", bg=BG_COLOR)
file_label2.pack(pady=5)

def load_city():
    path = browse_csv(file_label2)
    if path:
        run_city_check(path, city_output)

tk.Button(tab3, text="Browse CSV", bg=PRIMARY, fg="white", command=load_city).pack(pady=10)

city_output = tk.Text(tab3, height=20, width=100, bg="#fff0f6")
city_output.pack(pady=10)

# ------------------ ADD EXCEPTION PANEL
tk.Label(tab3, text="Add exception", font=("Roboto", 12, "bold"), bg=BG_COLOR).pack(pady=5)

edit_city = tk.Entry(tab3)
edit_city.pack()
edit_city.insert(0, "City")

edit_date = tk.Entry(tab3)
edit_date.pack()
edit_date.insert(0, "YYYY-MM-DD")

edit_open = tk.Entry(tab3)
edit_open.pack()
edit_open.insert(0, "Open HH:MM")

edit_close = tk.Entry(tab3)
edit_close.pack()
edit_close.insert(0, "Close HH:MM")

edit_reason = tk.Entry(tab3)
edit_reason.pack()
edit_reason.insert(0, "Reason")

edit_user = tk.Entry(tab3)
edit_user.pack()
edit_user.insert(0, "Edited by")

def save_exception():
    schedule = load_schedule()
    city = edit_city.get()

    if city not in schedule["cities"]:
        messagebox.showerror("Error", "City not found")
        return

    exception = {
        "date": edit_date.get(),
        "open": edit_open.get(),
        "close": edit_close.get(),
        "reason": edit_reason.get(),
        "edited_by": edit_user.get(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    schedule["cities"][city]["exceptions"].append(exception)
    save_schedule(schedule)
    messagebox.showinfo("Saved", "Exception added")

tk.Button(tab3, text="Save exception", bg=SECONDARY, command=save_exception).pack(pady=10)

# ------------------ TAB 4 WEATHER
tab4 = tk.Frame(notebook, bg=BG_COLOR)
notebook.add(tab4, text="Weather risk")

file_label3 = tk.Label(tab4, text="No file selected", bg=BG_COLOR)
file_label3.pack(pady=5)

def load_weather():
    path = browse_csv(file_label3)
    if path:
        check_weather(path, weather_output)

tk.Button(tab4, text="Browse CSV", bg=PRIMARY, fg="white", command=load_weather).pack(pady=10)

weather_output = tk.Text(tab4, height=20, width=100, bg="#fff0f6")
weather_output.pack(pady=10)

root.mainloop()

from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from tkinter import filedialog, Tk, messagebox
import os

def html_to_csv(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    records = []

    # Cada "outer-cell" es un bloque de video
    for outer in soup.find_all("div", class_="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp"):
        # Título del video
        title_div = outer.find("div", class_="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1")
        title = title_div.get_text(strip=True) if title_div else None

        # Fecha del video
        time_div = outer.find("div", class_="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption")
        time_str = time_div.get_text(strip=True) if time_div else None

        if title and time_str:
            try:
                dt = datetime.strptime(time_str, "%A, %B %d, %Y %I:%M:%S %p GMT%z")
                records.append([title, dt])
            except:
                continue

    if not records:
        print("No se encontraron vídeos en el HTML.")
        return

    df = pd.DataFrame(records, columns=["title", "datetime"])

    # Guardar CSV en la misma carpeta que el HTML
    csv_path = os.path.join(os.path.dirname(filepath), "youtube_watch_history.csv")
    df.to_csv(csv_path, index=False)
    print(f"CSV generado en: {csv_path}")
    return csv_path

# ===== TKINTER GUI =====
def launch_gui():
    root = Tk()
    root.withdraw()  # Oculta la ventana principal
    filepath = filedialog.askopenfilename(title="Selecciona watch-history.html", filetypes=[("HTML files", "*.html")])
    if not filepath:
        messagebox.showerror("Error", "No seleccionaste ningún archivo.")
        return

    csv_file = html_to_csv(filepath)
    if csv_file:
        messagebox.showinfo("Listo", f"CSV generado en:\n{csv_file}")

if __name__ == "__main__":
    launch_gui()
